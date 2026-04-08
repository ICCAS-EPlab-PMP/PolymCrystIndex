!##############################################################################
!#
!# @模块名称: miller_module (Miller指数模块)
!#
!# @功能描述: 
!#   本模块处理Miller指数相关的计算和匹配功能，类似于Python中的类(Class)。
!#   核心功能是将实验衍射点与理论晶面进行匹配。
!#
!# @主要功能:
!#   - Miller指数限制计算
!#   - 理论晶面遍历
!#   - 实验点与理论晶面的最佳匹配
!#   - 固定晶面处理
!#
!# @算法说明:
!#   使用OpenMP并行化遍历所有可能的(h,k,l)组合，
!#   对每个实验点找到误差最小的晶面匹配
!#
!# @使用说明:
!#   use miller_module
!#   call calculate_miller_limits(amax, bmax, cmax, wavelength, max_q, ...)
!#   call find_best_miller_indices(diffraction_num, parm, ...)
!#
!##############################################################################

module miller_module
    use fitting_module
    use crystal_module
    use diffraction_module
    implicit none
    
    ! 模块内部常量
    real*8, parameter :: PI = 3.14159265358979323846d0
    
    ! 并行计算相关私有变量（避免OpenMP共享变量问题）
    real*8 :: miller_wavelength
    real*8 :: miller_tilt_angle
    integer :: miller_tilt_check
    
contains

    !======================================================================
    ! @子程序: calculate_miller_limits
    ! @描述: 计算Miller指数的遍历限制
    !        
    ! @计算规则:
    !   1. 第一准则：三者都不能超过30
    !   2. 第二准则：根据amax, bmax, cmax和max(q)计算：max_index = amax * q / (2*pi) + 3
    !   3. 第三准则：按原算法计算：max_index = int(cell_param / wavelength)
    !   4. 第二与第三准则冲突时，取最大值
    !======================================================================
    subroutine calculate_miller_limits(amax, bmax, cmax, wavelength, max_q, &
                                       h_user_set, k_user_set, l_user_set)
        real*8, intent(in) :: amax, bmax, cmax, wavelength, max_q
        integer, intent(in) :: h_user_set, k_user_set, l_user_set
        
        ! 计算基于晶胞参数的Miller指数（第三准则）
        max_h1_by_cell = int(amax / wavelength)
        max_k1_by_cell = int(bmax / wavelength)
        max_l1_by_cell = int(cmax / wavelength)
        
        ! 限制在3-30之间
        max_h1_by_cell = max(3, min(30, max_h1_by_cell))
        max_k1_by_cell = max(3, min(30, max_k1_by_cell))
        max_l1_by_cell = max(3, min(30, max_l1_by_cell))
        
        ! 计算基于q值的Miller指数（第二准则）
        max_h1_by_q = int(amax * max_q / (2.0d0 * PI) + 3.0d0)
        max_k1_by_q = int(bmax * max_q / (2.0d0 * PI) + 3.0d0)
        max_l1_by_q = int(cmax * max_q / (2.0d0 * PI) + 3.0d0)
        
        ! 限制在5-30之间
        max_h1_by_q = max(5, min(30, max_h1_by_q))
        max_k1_by_q = max(5, min(30, max_k1_by_q))
        max_l1_by_q = max(5, min(30, max_l1_by_q))
        
        ! 确定最终Miller指数限制
        if (h_user_set == 1) then
            max_h1 = min(30, max_h1_in)
            if (max_h1 < 1) max_h1 = 5
        else
            max_h1 = max(max_h1_by_cell, max_h1_by_q)
            max_h1 = min(30, max_h1)
        end if
        
        if (k_user_set == 1) then
            max_k1 = min(30, max_k1_in)
            if (max_k1 < 1) max_k1 = 5
        else
            max_k1 = max(max_k1_by_cell, max_k1_by_q)
            max_k1 = min(30, max_k1)
        end if
        
        if (l_user_set == 1) then
            max_l1 = min(30, max_l1_in)
            if (max_l1 < 1) max_l1 = 5
        else
            max_l1 = max(max_l1_by_cell, max_l1_by_q)
            max_l1 = min(30, max_l1)
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: initialize_miller_trans
    ! @描述: 初始化Miller转换矩阵和误差列表
    !======================================================================
    subroutine initialize_miller_trans(diffraction_num)
        integer, intent(in) :: diffraction_num
        
        Miller_trans(:, 1) = 1
        Miller_trans(:, 2) = 0
        Miller_trans(:, 3) = 0
    end subroutine
    
    !======================================================================
    ! @子程序: find_best_miller_indices
    ! @描述: 寻找每个实验点的最佳Miller指数匹配
    !        
    ! @算法:
    !   外层循环遍历理论晶面 (h, k, l)
    !   内层循环对每个实验点计算误差，更新最小误差
    !   使用OpenMP并行化提高性能
    !======================================================================
    subroutine find_best_miller_indices(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real*8, intent(in) :: parm(:)
        
        ! 晶体参数
        real*8 :: a, b, c, alpha, beta, gamma
        real*8 :: V
        real*8 :: A11, B11, C11, D11, E11, F11
        
        ! Miller指数循环变量
        integer :: a1, b1, c1
        
        ! 中间计算变量
        real*8 :: theta, d, q, PHI, d1, y1
        real*8 :: tilt_angle, PHI_asin
        
        ! 误差计算相关
        real*8 :: error_mid
        integer :: k
        real*8, allocatable :: min_error_list(:)
        
        ! 初始化模块级变量（用于OpenMP）
        miller_wavelength = wavelength
        miller_tilt_check = tilt_check
        if (tilt_check == 1) then
            miller_tilt_angle = parm(7) * PI / 180.0d0
        else
            miller_tilt_angle = 0.0d0
        end if
        
        ! 读取晶胞参数
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
        call calculate_volume_direct(a, b, c, alpha, beta, gamma, V)
        call validate_volume(V)
        call calculate_reciprocal_params(a, b, c, alpha, beta, gamma, V, &
                                        A11, B11, C11, D11, E11, F11)
        
        ! 初始化
        allocate(min_error_list(diffraction_num))
        min_error_list = 1.0d10
        
        call initialize_miller_trans(diffraction_num)
        
        !======================================================================
        ! 并行循环：遍历所有Miller指数组合
        !======================================================================
        !$OMP PARALLEL DO COLLAPSE(3) DEFAULT(SHARED) &
        !$OMP PRIVATE(c1, b1, a1, y1, d, theta, q, d1, PHI_asin, PHI, k, error_mid) &
        !$OMP SCHEDULE(DYNAMIC)
        do c1 = 0, max_l1
            do b1 = -max_k1, max_k1
                do a1 = -max_h1, max_h1
                    
                    if (c1 == 0) then
                        y1 = 0.0d0
                    else
                        y1 = real(c1) / c
                    end if
                    
                    ! 跳过 (0,0,0)
                    if (a1 == 0 .and. b1 == 0 .and. c1 == 0) cycle
                    
                    ! 计算d间距
                    call calculate_d_spacing_direct(a1, b1, c1, &
                                                     A11, B11, C11, D11, E11, F11, V, d)
                    
                    ! 计算theta角
                    call calculate_theta_from_d(miller_wavelength, d, theta)
                    
                    ! 检查theta有效性
                    if (.not. check_theta_validity(theta)) cycle
                    
                    ! 计算q值
                    call calculate_q_from_d(d, q)
                    
                    ! 计算d1
                    call calculate_d1(miller_wavelength, d, d1)
                    
                    ! 计算PHI
                    if (miller_tilt_check == 1) then
                        call calculate_phi_with_tilt(y1, d, d1, theta, &
                                                     miller_tilt_angle, PHI)
                    else
                        call calculate_phi_without_tilt(y1, d1, PHI)
                    end if
                    
                    ! 对每个实验点计算误差并更新最小值
                    do k = 1, diffraction_num
                        if (level == 1) then
                            error_mid = abs(q - value1(k)) * e3 + &
                                       abs(PHI * 180.0d0 / PI - value(k)) * e2
                        else if (level == 2) then
                            error_mid = abs(q - value1(k)) * e3 + &
                                       abs(y1 - value(k)) * e2
                        end if
                        
                        ! 使用CRITICAL保护共享变量的更新
                        if (error_mid < min_error_list(k)) then
                            !$OMP CRITICAL(update_min)
                            if (error_mid < min_error_list(k)) then
                                min_error_list(k) = error_mid
                                Miller_trans(k, 1) = a1
                                Miller_trans(k, 2) = b1
                                Miller_trans(k, 3) = c1
                            end if
                            !$OMP END CRITICAL(update_min)
                        end if
                    end do
                    
                end do
            end do
        end do
        !$OMP END PARALLEL DO
        
        deallocate(min_error_list)
        
        ! 固定晶面处理
        call apply_fixed_hkl()
        
    end subroutine
    
    !======================================================================
    ! @子程序: apply_fixed_hkl
    ! @描述: 应用固定晶面设置，强制某些实验点使用指定的Miller指数
    !======================================================================
    subroutine apply_fixed_hkl()
        integer :: k
        
        if (allocated(fixhkl)) then
            do k = 1, fixhklfile
                Miller_trans(fixhkl(k, 1), 1:3) = fixhkl(k, 2:4)
            end do
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: apply_fixed_hkl_to_point
    ! @描述: 将固定Miller指数应用到单个实验点
    !======================================================================
    subroutine apply_fixed_hkl_to_point(point_idx, h, k, l)
        integer, intent(in) :: point_idx, h, k, l
        
        Miller_trans(point_idx, 1) = h
        Miller_trans(point_idx, 2) = k
        Miller_trans(point_idx, 3) = l
    end subroutine
    
    !======================================================================
    ! @函数: is_miller_index_valid
    ! @描述: 检查Miller指数是否在允许范围内
    !======================================================================
    function is_miller_index_valid(h, k, l) result(is_valid)
        integer, intent(in) :: h, k, l
        logical :: is_valid
        
        is_valid = (abs(h) <= max_h1 .and. &
                   abs(k) <= max_k1 .and. &
                   l >= 0 .and. l <= max_l1)
    end function
    
    !======================================================================
    ! @子程序: get_miller_index
    ! @描述: 获取指定实验点的Miller指数
    !======================================================================
    subroutine get_miller_index(point_idx, h, k, l)
        integer, intent(in) :: point_idx
        integer, intent(out) :: h, k, l
        
        h = int(Miller_trans(point_idx, 1))
        k = int(Miller_trans(point_idx, 2))
        l = int(Miller_trans(point_idx, 3))
    end subroutine
    
    !======================================================================
    ! @子程序: set_miller_index
    ! @描述: 设置指定实验点的Miller指数
    !======================================================================
    subroutine set_miller_index(point_idx, h, k, l)
        integer, intent(in) :: point_idx, h, k, l
        
        Miller_trans(point_idx, 1) = real(h)
        Miller_trans(point_idx, 2) = real(k)
        Miller_trans(point_idx, 3) = real(l)
    end subroutine

end module miller_module
