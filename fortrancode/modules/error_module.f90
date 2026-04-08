!##############################################################################
!#
!# @模块名称: error_module (误差计算模块)
!#
!# @功能描述: 
!#   本模块提供误差计算功能，类似于Python中的类(Class)。
!#   用于计算实验观测值与理论计算值之间的拟合误差。
!#
!# @主要功能:
!#   - 计算拟合误差
!#   - 计算拟合值（q, phi/y1）
!#   - 对称性权重处理
!#   - 参数边界惩罚
!#
!# @误差计算公式:
!#   level=1: error = |q_cal - q_obs|*e3 + |phi_cal - phi_obs|*e2 + V/e4
!#   level=2: error = |q_cal - q_obs|*e3 + |y1_cal - y1_obs|*e2 + V/e4
!#
!# @使用说明:
!#   use error_module
!#   call calcfiterr(diffraction_num, nparm, parm, fiterr, iflag)
!#   call error_cal_initial(diffraction_num, parm)
!#
!##############################################################################

module error_module
    use fitting_module
    use crystal_module
    use diffraction_module
    use miller_module
    implicit none
    
    ! 模块内部常量
    real*8, parameter :: PI = 3.14159265358979323846d0
    
contains

    !======================================================================
    ! @子程序: calcfiterr
    ! @描述: 计算拟合误差（供MINPACK调用）
    !        
    ! @输入参数:
    !   diffraction_num - 衍射点数量
    !   nparm - 参数数量
    !   parm - 参数数组
    !        
    ! @输出参数:
    !   fiterr - 误差数组
    !   iflag - 状态标志
    !======================================================================
    subroutine calcfiterr(diffraction_num, nparm, parm, fiterr, iflag)
        integer, intent(in) :: diffraction_num, nparm, iflag
        real*8, intent(in) :: parm(nparm)
        real*8, intent(out) :: fiterr(diffraction_num)
        
        real*8 :: fitval(diffraction_num), fitval1(diffraction_num)
        real*8 :: V
        integer :: i
        
        call calcfitval(diffraction_num, nparm, parm, fitval, fitval1, V)
        
        call calculate_fit_error(diffraction_num, nparm, parm, fitval, fitval1, V, fiterr)
        
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_fit_error
    ! @描述: 计算拟合误差的核心逻辑
    !======================================================================
    subroutine calculate_fit_error(diffraction_num, nparm, parm, fitval, fitval1, V, fiterr)
        integer, intent(in) :: diffraction_num, nparm
        real*8, intent(in) :: parm(nparm)
        real*8, intent(in) :: fitval(diffraction_num), fitval1(diffraction_num), V
        real*8, intent(out) :: fiterr(diffraction_num)
        
        integer :: i
        real*8 :: sym_cal
        
        sym_cal = 0.0d0
        if (sym_stat == 1) then
            do i = 4, 6
                if (abs(parm(i) - 90.0d0) < 2.0d0) then
                    sym_cal = sym_cal + 1.0d0
                end if
            end do
            
            if (sym_cal == 3.0d0) then
                fiterr(:) = (abs(fitval(1:diffraction_num) - value1(1:diffraction_num)) * e3 &
                        & + abs(fitval1(1:diffraction_num) - value(1:diffraction_num)) * e2 &
                        & + V / e4) * sym_e * contribution(1:diffraction_num)
            else if (sym_cal == 2.0d0) then
                fiterr(:) = (abs(fitval(1:diffraction_num) - value1(1:diffraction_num)) * e3 &
                        & + abs(fitval1(1:diffraction_num) - value(1:diffraction_num)) * e2 &
                        & + V / e4) * (0.5d0 + sym_e / 2.0d0) * contribution(1:diffraction_num)
            else
                fiterr(:) = abs(fitval(1:diffraction_num) - value1(1:diffraction_num)) * e3 &
                        & + abs(fitval1(1:diffraction_num) - value(1:diffraction_num)) * e2 &
                        & + V / e4 * contribution(1:diffraction_num)
            end if
        else
            fiterr(:) = abs(fitval(1:diffraction_num) - value1(1:diffraction_num)) * e3 &
                    & + abs(fitval1(1:diffraction_num) - value(1:diffraction_num)) * e2 &
                    & + V / e4 * contribution(1:diffraction_num)
        end if
        
        ! 参数边界惩罚
        call apply_boundary_penalty(diffraction_num, fiterr)
        
    end subroutine
    
    !======================================================================
    ! @子程序: apply_boundary_penalty
    ! @描述: 对超出边界的参数应用5倍惩罚
    !======================================================================
    subroutine apply_boundary_penalty(diffraction_num, nparm, parm, fiterr)
        integer, intent(in) :: diffraction_num, nparm
        real*8, intent(in) :: parm(nparm)
        real*8, intent(inout) :: fiterr(diffraction_num)
        
        if (sym_cal <= 1.0d0) then
            if (any(parm(1:6) > max_values)) then
                fiterr(:) = fiterr(:) * 5.0d0
            end if
            
            if (any(parm(1:6) < min_values)) then
                fiterr(:) = fiterr(:) * 5.0d0
            end if
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: error_cal_initial
    ! @描述: 初始误差校准，寻找最佳Miller指数匹配
    !        这是优化前的预处理步骤
    !======================================================================
    subroutine error_cal_initial(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real*8, intent(inout) :: parm(:)
        
        call find_best_miller_indices(diffraction_num, parm)
        
    end subroutine
    
    !======================================================================
    ! @子程序: calcfitval
    ! @描述: 计算拟合值（q值和phi/y1值）
    !        
    ! @输入参数:
    !   diffraction_num - 衍射点数量
    !   nparm - 参数数量
    !   parm - 参数数组
    !        
    ! @输出参数:
    !   fitval - 计算的q值
    !   fitval1 - 计算的phi值或y1值
    !   V - 晶体体积
    !======================================================================
    subroutine calcfitval(diffraction_num, nparm, parm, fitval, fitval1, V)
        use fitting_module
        integer, intent(in) :: diffraction_num, nparm
        real*8, intent(in) :: parm(nparm)
        real*8, intent(out) :: fitval(diffraction_num), fitval1(diffraction_num), V
        
        real*8 :: a, b, c, alpha, beta, gamma
        real*8 :: A11, B11, C11, D11, E11, F11
        real*8 :: h1, k1, l1
        real*8 :: q, PHI, d, d1, y1
        real*8 :: tilt_angle, PHI_asin, theta
        integer :: i
        
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
        
        tilt_angle = 0.0d0
        if (tilt_check == 1) then
            tilt_angle = parm(7) * PI / 180.0d0
        end if
        
        call calculate_volume_direct(a, b, c, alpha, beta, gamma, V)
        call validate_volume(V)
        
        PHI = 0.0d0
        
        call calculate_reciprocal_params(a, b, c, alpha, beta, gamma, V, &
                                         A11, B11, C11, D11, E11, F11)
        
        do i = 1, diffraction_num
            h1 = Miller_trans(i, 1)
            k1 = Miller_trans(i, 2)
            l1 = Miller_trans(i, 3)
            
            call calculate_y1(int(l1), c, y1)
            
            call calculate_d_spacing_direct(int(h1), int(k1), int(l1), &
                                            A11, B11, C11, D11, E11, F11, V, d)
            
            call calculate_theta_from_d(wavelength, d, theta)
            call calculate_q_from_d(d, q)
            call calculate_d1(wavelength, d, d1)
            
            if (tilt_check == 1) then
                call calculate_phi_with_tilt(y1, d, d1, theta, tilt_angle, PHI)
            else
                call calculate_phi_without_tilt(y1, d1, PHI)
            end if
            
            fitval(i) = q
            
            if (level == 1) then
                fitval1(i) = PHI * 180.0d0 / PI
            else if (level == 2) then
                fitval1(i) = y1
            end if
            
        end do
        
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_single_error
    ! @描述: 计算单个衍射点的误差
    !======================================================================
    subroutine calculate_single_error(q_calc, phi_calc, q_obs, phi_obs, V, error)
        real*8, intent(in) :: q_calc, phi_calc, q_obs, phi_obs, V
        real*8, intent(out) :: error
        
        error = abs(q_calc - q_obs) * e3 + abs(phi_calc - phi_obs) * e2 + V / e4
    end subroutine
    
    !======================================================================
    ! @函数: get_symmetry_factor
    ! @描述: 根据对称性计算权重因子
    !======================================================================
    function get_symmetry_factor(parm) result(sym_factor)
        real*8, intent(in) :: parm(:)
        real*8 :: sym_factor
        integer :: i
        
        sym_factor = 0.0d0
        if (sym_stat == 1) then
            do i = 4, 6
                if (abs(parm(i) - 90.0d0) < 2.0d0) then
                    sym_factor = sym_factor + 1.0d0
                end if
            end do
            
            if (sym_factor == 3.0d0) then
                sym_factor = sym_e
            else if (sym_factor == 2.0d0) then
                sym_factor = 0.5d0 + sym_e / 2.0d0
            else
                sym_factor = 1.0d0
            end if
        else
            sym_factor = 1.0d0
        end if
    end function

end module error_module
