!##############################################################################
!#
!# @文件名称: polycry_lib.f90 (POLYCRY纤维衍射分析库)
!#
!# @功能描述: 
!#   本文件是POLYCRY纤维衍射分析库的完整整合版本。
!#   包含所有模块，可作为单一文件使用。
!#
!# @模块列表:
!#   1. fitting_module   - 参数配置模块
!#   2. crystal_module    - 晶体计算模块
!#   3. diffraction_module - 衍射计算模块
!#   4. miller_module     - Miller指数模块
!#   5. error_module      - 误差计算模块
!#   6. minpack_module    - MINPACK优化库
!#   7. io_module         - 输入输出模块
!#
!# @使用方法:
!#   在您的程序中使用:
!#     use polycry_lib
!#   或者单独使用某个模块:
!#     use fitting_module
!#     use crystal_module
!#     use diffraction_module
!#     use miller_module
!#     use error_module
!#     use minpack_module
!#     use io_module
!#
!# @程序主文件:
!#   使用 polycry_main.f90 作为主程序入口
!#
!##############################################################################

!##############################################################################
! 模块1: fitting_module (参数配置模块)
!##############################################################################
module fitting_module
    implicit none
    
    real*8, parameter :: PI = 3.14159265358979323846d0
    integer, parameter :: maxdata = 1000
    
    real*8 :: x(maxdata)
    real*8 :: value(maxdata), value1(maxdata)
    real*8 :: e2, e3, e4, wavelength, x1, sym_e, sym_cal
    real*8 :: Miller_trans(maxdata, 3)
    integer :: sym_stat
    integer :: level
    real*8 :: contribution(maxdata)
    integer :: tilt_check
    integer :: crystal_system
    integer :: fixhklfile
    integer, allocatable :: fixhkl(:,:)
    integer :: ortho_ab_star
    
    integer :: max_h1_in, max_k1_in, max_l1_in
    integer :: max_h1, max_k1, max_l1
    integer :: h_user_set, k_user_set, l_user_set
    real*8 :: max_q
    integer :: max_h1_by_cell, max_k1_by_cell, max_l1_by_cell
    integer :: max_h1_by_q, max_k1_by_q, max_l1_by_q
    real*8 :: max_values(6), min_values(6)
    
    integer :: num_cell
    real*8 :: amin, bmin, cmin, alphamin, betamin, gammamin
    real*8 :: amax, bmax, cmax, alphamax, betamax, gammamax
    
end module fitting_module

!##############################################################################
! 模块2: crystal_module (晶体计算模块)
!##############################################################################
module crystal_module
    use fitting_module
    implicit none
    
    interface init_crystal_parameters
        module procedure init_crystal_parameters_with_tilt
        module procedure init_crystal_parameters_without_tilt
    end interface
    
    interface calculate_volume
        module procedure calculate_volume_direct
    end interface
    
    interface calculate_reciprocal_parameters
        module procedure calculate_reciprocal_params
    end interface

contains

    subroutine init_crystal_parameters_with_tilt(parm, a, b, c, alpha, beta, gamma, tilt_angle)
        real*8, intent(in) :: parm(:)
        real*8, intent(out) :: a, b, c, alpha, beta, gamma, tilt_angle
        
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        tilt_angle = 0.0d0
        if (tilt_check == 1) then
            tilt_angle = parm(7) * PI / 180.0d0
        end if
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
    end subroutine
    
    subroutine init_crystal_parameters_without_tilt(parm, a, b, c, alpha, beta, gamma)
        real*8, intent(in) :: parm(:)
        real*8, intent(out) :: a, b, c, alpha, beta, gamma
        
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
    end subroutine
    
    subroutine calculate_crystal_angles(parm, alpha, beta, gamma)
        real*8, intent(in) :: parm(:)
        real*8, intent(out) :: alpha, beta, gamma
        
        if (ortho_ab_star == 1) then
            alpha = parm(4) * PI / 180.0d0
            beta = parm(5) * PI / 180.0d0
            gamma = acos(cos(alpha) * cos(beta))
        else if (crystal_system == 1) then
            alpha = PI / 2.0d0
            beta = PI / 2.0d0
            gamma = PI / 2.0d0
        else
            alpha = parm(4) * PI / 180.0d0
            beta = parm(5) * PI / 180.0d0
            gamma = parm(6) * PI / 180.0d0
        end if
    end subroutine
    
    subroutine calculate_volume_direct(a, b, c, alpha, beta, gamma, V)
        real*8, intent(in) :: a, b, c, alpha, beta, gamma
        real*8, intent(out) :: V
        
        real*8 :: cos_alpha, cos_beta, cos_gamma
        
        cos_alpha = cos(alpha)
        cos_beta = cos(beta)
        cos_gamma = cos(gamma)
        
        V = a * b * c * sqrt(1.0d0 - cos_alpha**2 - cos_beta**2 - cos_gamma**2 + &
                            2.0d0 * cos_alpha * cos_beta * cos_gamma)
        
        if (isnan(V) .or. V < 0.01d0) then
            V = 10000000.0d0
        end if
    end subroutine
    
    subroutine validate_volume(V)
        real*8, intent(inout) :: V
        
        if (isnan(V) .or. V < 0.01d0) then
            V = 10000000.0d0
        end if
    end subroutine
    
    subroutine calculate_reciprocal_params(a, b, c, alpha, beta, gamma, V, &
                                           A11, B11, C11, D11, E11, F11)
        real*8, intent(in) :: a, b, c, alpha, beta, gamma, V
        real*8, intent(out) :: A11, B11, C11, D11, E11, F11
        
        real*8 :: cos_alpha, cos_beta, cos_gamma, sin_alpha
        
        cos_alpha = cos(alpha)
        cos_beta = cos(beta)
        cos_gamma = cos(gamma)
        sin_alpha = sin(alpha)
        
        A11 = b**2 * c**2 * sin_alpha**2
        B11 = a**2 * c**2 * sin(beta)**2
        C11 = a**2 * b**2 * sin(gamma)**2
        D11 = a * b * c**2 * (cos_alpha * cos_beta - cos_gamma)
        E11 = a**2 * b * c * (cos_beta * cos_gamma - cos_alpha)
        F11 = a * b**2 * c * (cos_gamma * cos_alpha - cos_beta)
    end subroutine

end module crystal_module

!##############################################################################
! 模块3: diffraction_module (衍射计算模块)
!##############################################################################
module diffraction_module
    use fitting_module
    implicit none
    
    interface calculate_d_spacing
        module procedure calculate_d_spacing_direct
    end interface
    
    interface calculate_q
        module procedure calculate_q_from_d
    end interface
    
    interface calculate_theta
        module procedure calculate_theta_from_d
    end interface
    
    interface calculate_phi
        module procedure calculate_phi_with_tilt
        module procedure calculate_phi_without_tilt
    end interface

contains

    subroutine calculate_d_spacing_direct(h, k, l, A11, B11, C11, D11, E11, F11, V, d)
        integer, intent(in) :: h, k, l
        real*8, intent(in) :: A11, B11, C11, D11, E11, F11, V
        real*8, intent(out) :: d
        
        real*8 :: numerator, denominator
        
        numerator = A11 * real(h)**2 + B11 * real(k)**2 + C11 * real(l)**2 + &
                    2.0d0 * D11 * real(h) * real(k) + &
                    2.0d0 * E11 * real(k) * real(l) + &
                    2.0d0 * F11 * real(h) * real(l)
        
        denominator = (V ** 2)
        
        if (denominator > 0.0d0) then
            d = 1.0d0 / sqrt(numerator / denominator)
        else
            d = 0.0d0
        end if
    end subroutine
    
    subroutine calculate_q_from_d(d, q)
        real*8, intent(in) :: d
        real*8, intent(out) :: q
        
        if (d > 0.0d0) then
            q = 2.0d0 * PI / d
        else
            q = 0.0d0
        end if
    end subroutine
    
    subroutine calculate_theta_from_d(wavelength, d, theta)
        real*8, intent(in) :: wavelength, d
        real*8, intent(out) :: theta
        
        real*8 :: sin_theta
        
        if (d > 0.0d0) then
            sin_theta = wavelength / (2.0d0 * d)
            if (abs(sin_theta) > 1.0d0) then
                theta = 0.0d0
            else
                theta = asin(sin_theta)
            end if
        else
            theta = 0.0d0
        end if
    end subroutine
    
    subroutine calculate_d1(wavelength, d, d1)
        real*8, intent(in) :: wavelength, d
        real*8, intent(out) :: d1
        
        if (d > 0.0d0) then
            d1 = sqrt(4.0d0 * d**2 - wavelength**2) / (2.0d0 * d**2)
        else
            d1 = 0.0d0
        end if
    end subroutine
    
    subroutine calculate_y1(l, c, y1)
        integer, intent(in) :: l
        real*8, intent(in) :: c
        real*8, intent(out) :: y1
        
        if (l == 0) then
            y1 = 0.0d0
        else
            y1 = real(l) / c
        end if
    end subroutine
    
    subroutine calculate_phi_with_tilt(y1, d, d1, theta, tilt_angle, PHI)
        real*8, intent(in) :: y1, d, d1, theta, tilt_angle
        real*8, intent(out) :: PHI
        
        real*8 :: PHI_asin
        real*8 :: cos_tilt, tan_tilt
        
        cos_tilt = cos(tilt_angle)
        tan_tilt = tan(tilt_angle)
        
        PHI_asin = (y1 / cos_tilt + (1.0d0 / d) * sin(theta) * tan_tilt) / d1
        
        if (PHI_asin > 1.0d0 .or. PHI_asin < -1.0d0) then
            PHI = PI / 2.0d0
        else
            PHI = asin(PHI_asin)
        end if
    end subroutine
    
    subroutine calculate_phi_without_tilt(y1, d1, PHI)
        real*8, intent(in) :: y1, d1
        real*8, intent(out) :: PHI
        
        if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
            PHI = PI / 2.0d0
        else
            PHI = asin(y1 / d1)
        end if
    end subroutine
    
    function check_theta_validity(theta) result(is_valid)
        real*8, intent(in) :: theta
        logical :: is_valid
        
        is_valid = (theta == theta)
    end function

end module diffraction_module

!##############################################################################
! 模块4: miller_module (Miller指数模块)
!##############################################################################
module miller_module
    use fitting_module
    use crystal_module
    use diffraction_module
    implicit none
    
    real*8 :: miller_wavelength
    real*8 :: miller_tilt_angle
    integer :: miller_tilt_check
    
contains

    subroutine calculate_miller_limits(amax, bmax, cmax, wavelength, max_q, &
                                      h_user_set, k_user_set, l_user_set)
        real*8, intent(in) :: amax, bmax, cmax, wavelength, max_q
        integer, intent(in) :: h_user_set, k_user_set, l_user_set
        
        max_h1_by_cell = int(amax / wavelength)
        max_k1_by_cell = int(bmax / wavelength)
        max_l1_by_cell = int(cmax / wavelength)
        
        max_h1_by_cell = max(3, min(30, max_h1_by_cell))
        max_k1_by_cell = max(3, min(30, max_k1_by_cell))
        max_l1_by_cell = max(3, min(30, max_l1_by_cell))
        
        max_h1_by_q = int(amax * max_q / (2.0d0 * PI) + 3.0d0)
        max_k1_by_q = int(bmax * max_q / (2.0d0 * PI) + 3.0d0)
        max_l1_by_q = int(cmax * max_q / (2.0d0 * PI) + 3.0d0)
        
        max_h1_by_q = max(5, min(30, max_h1_by_q))
        max_k1_by_q = max(5, min(30, max_k1_by_q))
        max_l1_by_q = max(5, min(30, max_l1_by_q))
        
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
    
    subroutine initialize_miller_trans(diffraction_num)
        integer, intent(in) :: diffraction_num
        
        Miller_trans(:, 1) = 1
        Miller_trans(:, 2) = 0
        Miller_trans(:, 3) = 0
    end subroutine
    
    subroutine find_best_miller_indices(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real*8, intent(in) :: parm(:)
        
        real*8 :: a, b, c, alpha, beta, gamma
        real*8 :: V
        real*8 :: A11, B11, C11, D11, E11, F11
        
        integer :: a1, b1, c1
        real*8 :: theta, d, q, PHI, d1, y1
        real*8 :: tilt_angle, PHI_asin
        real*8 :: error_mid
        integer :: k
        real*8, allocatable :: min_error_list(:)
        
        miller_wavelength = wavelength
        miller_tilt_check = tilt_check
        if (tilt_check == 1) then
            miller_tilt_angle = parm(7) * PI / 180.0d0
        else
            miller_tilt_angle = 0.0d0
        end if
        
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
        call calculate_volume_direct(a, b, c, alpha, beta, gamma, V)
        call validate_volume(V)
        call calculate_reciprocal_params(a, b, c, alpha, beta, gamma, V, &
                                        A11, B11, C11, D11, E11, F11)
        
        allocate(min_error_list(diffraction_num))
        min_error_list = 1.0d10
        
        call initialize_miller_trans(diffraction_num)
        
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
                    
                    if (a1 == 0 .and. b1 == 0 .and. c1 == 0) cycle
                    
                    call calculate_d_spacing_direct(a1, b1, c1, &
                                                     A11, B11, C11, D11, E11, F11, V, d)
                    
                    call calculate_theta_from_d(miller_wavelength, d, theta)
                    
                    if (.not. check_theta_validity(theta)) cycle
                    
                    call calculate_q_from_d(d, q)
                    call calculate_d1(miller_wavelength, d, d1)
                    
                    if (miller_tilt_check == 1) then
                        call calculate_phi_with_tilt(y1, d, d1, theta, &
                                                     miller_tilt_angle, PHI)
                    else
                        call calculate_phi_without_tilt(y1, d1, PHI)
                    end if
                    
                    do k = 1, diffraction_num
                        if (level == 1) then
                            error_mid = abs(q - value1(k)) * e3 + &
                                       abs(PHI * 180.0d0 / PI - value(k)) * e2
                        else if (level == 2) then
                            error_mid = abs(q - value1(k)) * e3 + &
                                       abs(y1 - value(k)) * e2
                        end if
                        
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
        
        call apply_fixed_hkl()
        
    end subroutine
    
    subroutine apply_fixed_hkl()
        integer :: k
        
        if (allocated(fixhkl)) then
            do k = 1, fixhklfile
                Miller_trans(fixhkl(k, 1), 1:3) = fixhkl(k, 2:4)
            end do
        end if
    end subroutine

end module miller_module

!##############################################################################
! 模块5: error_module (误差计算模块)
!##############################################################################
module error_module
    use fitting_module
    use crystal_module
    use diffraction_module
    use miller_module
    implicit none
    
    real*8 :: sym_cal
    
contains

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
    
    subroutine calculate_fit_error(diffraction_num, nparm, parm, fitval, fitval1, V, fiterr)
        integer, intent(in) :: diffraction_num, nparm
        real*8, intent(in) :: parm(nparm)
        real*8, intent(in) :: fitval(diffraction_num), fitval1(diffraction_num), V
        real*8, intent(out) :: fiterr(diffraction_num)
        
        integer :: i
        
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
        
        if (sym_cal <= 1.0d0) then
            if (any(parm(1:6) > max_values)) then
                fiterr(:) = fiterr(:) * 5.0d0
            end if
            
            if (any(parm(1:6) < min_values)) then
                fiterr(:) = fiterr(:) * 5.0d0
            end if
        end if
        
    end subroutine
    
    subroutine error_cal_initial(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real*8, intent(inout) :: parm(:)
        
        call find_best_miller_indices(diffraction_num, parm)
        
    end subroutine
    
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

end module error_module

!##############################################################################
! 模块6: minpack_module (MINPACK优化库模块)
!##############################################################################
module minpack_module
    implicit none
    
    integer :: minpack_n
    integer :: minpack_m
    
contains

    subroutine lmdif1(fcn, m, n, x, fvec, tol, maxfev, info)
        external fcn
        integer, intent(in) :: m, n, maxfev
        integer, intent(out) :: info
        real*8, intent(inout) :: x(n), fvec(m)
        real*8, intent(in) :: tol
        
        integer :: lwa
        real*8, allocatable :: wa(:)
        integer :: nfev
        integer :: ldfjac
        real*8 :: ftol, gtol, xtol
        integer :: mode, nprint
        real*8 :: factor
        integer :: maxfev_internal
        integer :: info_internal
        
        ldfjac = m
        lwa = m * n + 5 * n + m
        allocate(wa(lwa))
        
        ftol = tol
        xtol = tol
        gtol = 1.0d-10
        mode = 1
        nprint = 0
        factor = 100.0d0
        maxfev_internal = maxfev
        nfev = 0
        info_internal = 0
        
        call lmdif(fcn, m, n, x, fvec, ftol, xtol, gtol, maxfev_internal, &
                   mode, factor, nprint, info_internal, nfev, wa, lwa)
        
        info = info_internal
        
        deallocate(wa)
        
    end subroutine
    
    subroutine lmdif(fcn, m, n, x, fvec, ftol, xtol, gtol, maxfev, &
                      mode, factor, nprint, info, nfev, wa, lwa)
        external fcn
        integer m, n, maxfev, mode, nprint, info, nfev, lwa
        real*8 x(n), fvec(m), ftol, xtol, gtol, factor, wa(lwa)
        
        integer :: i, iflag
        integer :: iter
        real*8 :: actred, delta, dirder, epsmch, fnorm, fnorm1
        real*8 :: gnorm, par, pnorm, prered, ratio, sum2
        integer :: nfev_count
        
        epsmch = epsilon(epsmch)
        
        info = 0
        iflag = 0
        nfev = 0
        par = 0.0d0
        
        if (n <= 0 .or. m < n .or. ftol < 0.0d0 .or. xtol < 0.0d0 &
            .or. gtol < 0.0d0 .or. maxfev <= 0 .or. factor <= 0.0d0) then
            return
        end if
        
        iflag = 1
        call fcn(m, n, x, fvec, iflag)
        nfev = 1
        
        if (iflag < 0) then
            info = iflag
            return
        end if
        
        fnorm = enorm(m, fvec)
        
        iter = 1
        delta = factor * sqrt(dble(n))
        
        do while (nfev < maxfev)
            iflag = 2
            call fdjac2(fcn, m, n, x, fvec, wa, n, iflag, epsmch)
            nfev = nfev + n
            
            if (iflag < 0) then
                info = iflag
                return
            end if
            
            call qrfac(m, n, wa, n, .true., 1, 1, wa(n+1), wa(2*n+1))
            
            if (iter == 1) then
                if (mode /= 2) then
                    do i = 1, n
                        if (wa(n+i) == 0.0d0) wa(n+i) = 1.0d0
                    end do
                end if
            end if
            
            do i = 1, n
                wa(3*n+i) = dot_product(fvec, wa(1:m+(i-1)*m))
            end do
            
            call dogleg(n, wa, n, wa(n+1), wa(3*n+1), delta, wa(2*n+1))
            
            pnorm = enorm(n, wa(n+1))
            
            wa(4*n+1:5*n) = x(1:n)
            x(1:n) = x(1:n) - wa(2*n+1:3*n)
            
            iflag = 1
            call fcn(m, n, x, fvec, iflag)
            nfev = nfev + 1
            
            if (iflag < 0) then
                info = iflag
                return
            end if
            
            fnorm1 = enorm(m, fvec)
            
            actred = fnorm - fnorm1
            
            if (actred > 0.0d0 .and. pnorm > 0.0d0) then
                prered = -actred
                ratio = actred / prered
            else
                ratio = 0.0d0
            end if
            
            if (ratio < 0.25d0) then
                delta = 0.5d0 * delta
            else if (ratio > 0.75d0) then
                delta = max(delta, pnorm / 0.5d0)
            end if
            
            if (ratio >= 0.0001d0) then
                x(1:n) = wa(2*n+1:3*n)
            else
                x(1:n) = wa(4*n+1:5*n)
            end if
            
            if (abs(actred) <= ftol .and. pnorm <= xtol .and. ratio >= 0.0001d0) then
                info = 1
                return
            end if
            
            if (abs(actred) <= epsmch .and. pnorm <= epsmch .and. ratio >= 0.0001d0) then
                info = 2
                return
            end if
            
            if (delta <= xtol) then
                info = 3
                return
            end if
            
            iter = iter + 1
        end do
        
        info = 4
        
    end subroutine
    
    subroutine fdjac2(fcn, m, n, x, fvec, fjac, ldfjac, iflag, epsfcn)
        external fcn
        integer m, n, ldfjac, iflag
        real*8 x(n), fvec(m), fjac(ldfjac,n), epsfcn
        
        real*8 :: eps
        real*8 :: epsmch
        real*8 :: h
        integer :: j
        real*8 :: temp
        real*8, allocatable :: wa(:)
        
        epsmch = epsilon(epsmch)
        eps = sqrt(max(epsfcn, epsmch))
        
        allocate(wa(m))
        
        do j = 1, n
            temp = x(j)
            h = eps * abs(temp)
            if (h == 0.0d0) h = eps
            
            x(j) = temp + h
            iflag = 1
            call fcn(m, n, x, wa, iflag)
            
            if (iflag < 0) then
                x(j) = temp
                deallocate(wa)
                return
            end if
            
            x(j) = temp
            fjac(1:m, j) = (wa(1:m) - fvec(1:m)) / h
        end do
        
        deallocate(wa)
        
    end subroutine
    
    subroutine dogleg(n, r, lr, diag, qtb, delta, x)
        integer n, lr
        real*8 r(lr), diag(n), qtb(n), delta, x(n)
        
        real*8 :: alpha, bnorm, gnorm
        integer :: i, j, jj, k, l
        real*8 :: qnorm, sgnorm, sum2, temp, epsmch
        real*8, allocatable :: wa1(:), wa2(:)
        
        allocate(wa1(n), wa2(n))
        
        epsmch = epsilon(epsmch)
        
        jj = (n * (n + 1)) / 2 + 1
        do k = 1, n
            j = n - k + 1
            jj = jj - k
            l = jj + 1
            sum2 = 0.0d0
            do i = j + 1, n
                sum2 = sum2 + r(l) * x(i)
                l = l + 1
            end do
            temp = r(jj)
            if (temp == 0.0d0) then
                l = j
                do i = 1, j
                    temp = max(temp, abs(r(l)))
                    l = l + n - i
                end do
                if (temp == 0.0d0) temp = epsmch
            end if
            x(j) = (qtb(j) - sum2) / temp
        end do
        
        wa1(1:n) = 0.0d0
        wa2(1:n) = diag(1:n) * x(1:n)
        qnorm = enorm(n, wa2)
        
        if (qnorm <= delta) then
            deallocate(wa1, wa2)
            return
        end if
        
        l = 1
        do j = 1, n
            temp = qtb(j)
            do i = j, n
                wa1(i) = wa1(i) + r(l) * temp
                l = l + 1
            end do
            wa1(j) = wa1(j) / diag(j)
        end do
        
        gnorm = enorm(n, wa1)
        sgnorm = 0.0d0
        alpha = delta / qnorm
        
        if (gnorm /= 0.0d0) then
            wa1(1:n) = (wa1(1:n) / gnorm) / diag(1:n)
            
            l = 1
            do j = 1, n
                sum2 = 0.0d0
                do i = j, n
                    sum2 = sum2 + r(l) * wa1(i)
                    l = l + 1
                end do
                wa2(j) = sum2
            end do
            
            temp = enorm(n, wa2)
            sgnorm = (gnorm / temp) / temp
            
            alpha = 0.0d0
            
            if (sgnorm < delta) then
                bnorm = enorm(n, qtb)
                temp = (bnorm / gnorm) * (bnorm / qnorm) * (sgnorm / delta)
                temp = temp - (delta / qnorm) * (sgnorm / delta)**2 &
                     + sqrt((temp - (delta / qnorm))**2 &
                     + (1.0d0 - (delta / qnorm)**2) &
                     * (1.0d0 - (sgnorm / delta)**2))
                
                alpha = ((delta / qnorm) * (1.0d0 - (sgnorm / delta)**2)) / temp
            end if
        end if
        
        temp = (1.0d0 - alpha) * min(sgnorm, delta)
        x(1:n) = temp * wa1(1:n) + alpha * x(1:n)
        
        deallocate(wa1, wa2)
        
    end subroutine
    
    function enorm(n, x) result(res)
        integer, intent(in) :: n
        real*8, intent(in) :: x(n)
        real*8 :: res
        
        res = sqrt(sum(x(1:n)**2))
        
    end function
    
    subroutine qrfac(m, n, a, lda, pivot, ipvt, Ritz, diag, qnorm)
        logical, intent(in) :: pivot
        integer, intent(in) :: m, n, lda, Ritz
        integer, intent(out) :: ipvt(n)
        real*8, intent(inout) :: a(lda,n)
        real*8, intent(out) :: diag(n), qnorm(n)
        
        integer :: i, j, k, jmax, minmn
        real*8 :: ajnorm, temp, epsmch
        real*8, allocatable :: wa(:)
        
        epsmch = epsilon(epsmch)
        allocate(wa(n))
        
        do j = 1, n
            diag(j) = 0.0d0
            qnorm(j) = 0.0d0
        end do
        
        do i = 1, m
            wa(1:n) = a(i, 1:n)
            do j = 1, n
                diag(j) = max(diag(j), abs(a(i,j)))
            end do
        end do
        
        minmn = min(m, n)
        do j = 1, minmn
            if (pivot) then
                jmax = j
                do k = j + 1, n
                    if (abs(a(jmax,j)) < abs(a(k,j))) then
                        jmax = k
                    end if
                end do
                if (jmax /= j) then
                    do i = 1, m
                        temp = a(i,j)
                        a(i,j) = a(i,jmax)
                        a(i,jmax) = temp
                    end do
                    diag(jmax) = diag(j)
                end if
                ipvt(j) = jmax
            else
                ipvt(j) = j
            end if
            
            if (j < m) then
                ajnorm = enorm(m-j+1, a(j:m,j))
                if (ajnorm /= 0.0d0) then
                    if (a(j,j) /= 0.0d0) ajnorm = sign(ajnorm, a(j,j))
                    a(j:m,j) = a(j:m,j) / ajnorm
                    a(j,j) = a(j,j) + 1.0d0
                end if
            end if
            
            qnorm(j) = ajnorm
        end do
        
        deallocate(wa)
        
    end subroutine

end module minpack_module

!##############################################################################
! 模块7: io_module (输入输出模块)
!##############################################################################
module io_module
    use fitting_module
    implicit none
    
contains

    subroutine parse_command_arguments(input_type, filename1, input_type2, &
                                       filename2, input_type3, filename3, &
                                       filename_input, filename_cell, filename_dif)
        character(len=512), intent(out) :: input_type, filename1, input_type2, &
                                          filename2, input_type3, filename3
        character(len=512), intent(out) :: filename_input, filename_cell, filename_dif
        
        call get_command_argument(1, input_type)
        call get_command_argument(2, filename1)
        call get_command_argument(3, input_type2)
        call get_command_argument(4, filename2)
        call get_command_argument(5, input_type3)
        call get_command_argument(6, filename3)
        
        if (input_type == '-i' .or. input_type == '-input') then
            filename_input = filename1
            if (input_type2 == '-c' .or. input_type2 == '-crystal') then
                filename_cell = filename2
                filename_dif = filename3
            else if (input_type2 == '-d' .or. input_type2 == '-diffrac') then
                filename_dif = filename2
                filename_cell = filename3
            end if
        else if (input_type == '-c' .or. input_type == '-crystal') then
            filename_cell = filename1
            if (input_type2 == '-i' .or. input_type2 == '-input') then
                filename_input = filename2
                filename_dif = filename3
            else if (input_type2 == '-d' .or. input_type2 == '-diffrac') then
                filename_dif = filename2
                filename_input = filename3
            end if
        else if (input_type == '-d' .or. input_type == '-diffrac') then
            filename_dif = filename1
            if (input_type2 == '-i' .or. input_type2 == '-input') then
                filename_input = filename2
                filename_cell = filename3
            else if (input_type2 == '-c' .or. input_type2 == '-crystal') then
                filename_cell = filename2
                filename_input = filename3
            end if
        else
            call print_usage_error()
        end if
        
    end subroutine
    
    subroutine print_usage_error()
        write(*,*) 'Wrong Input_type!!, choosen command line: -i,-input,-c,-crystal,-d,-diffrac'
        write(*,*) " "
        write(*,*) "========================VERSION 1.6=========================="
        write(*,*) "RELEASE in 2026.3.16"
        write(*,*) " "
        write(*,*) "-------------------------REFERENCE-------------------"
        write(*,*) " This software utilizes the MINPACK library for nonlinear optimization."
        write(*,*) " Software base on following MINPACK references:"
        write(*,*) " "
        write(*,*) " Jorge More, Burton Garbow, Kenneth Hillstrom,"
        write(*,*) " User Guide for MINPACK-1,"
        write(*,*) " Technical Report ANL-80-74,"
        write(*,*) " Argonne National Laboratory, 1980."
        write(*,*) "----------------------------------------------------------------------"
        
        read(*,*)
        stop 'Wrong Input_type!!, choosen -i,-input,-c,-crystal,-d,-diffrac'
    end subroutine
    
    subroutine read_input_file(filename_input)
        character(len=512), intent(in) :: filename_input
        
        character(len=256) :: buffer
        integer :: io_status
        integer :: i
        
        open(unit=1, file=filename_input, status='old', action='read')
        
        fixhklfile = 0
        ortho_ab_star = 0
        
        do i = 1, 28
            if (i == 1) then
                read(1, *) wavelength
            else if (i == 4) then
                read(1, *) num_cell
            else if (i == 13) then
                read(1, *) level
            else if (i == 14) then
                read(1, *) ortho_ab_star
            else if (i == 15) then
                read(1, *) e2
            else if (i == 16) then
                read(1, *) e3
            else if (i == 17) then
                read(1, *) e4
            else if (i == 18) then
                read(1, *) x1
            else if (i == 19) then
                read(1, '(A)') buffer
                read(buffer, *, iostat=io_status) max_h1_in, max_k1_in, max_l1_in
                if (io_status /= 0) then
                    read(buffer, *, iostat=io_status) max_h1_in
                    if (io_status == 0 .and. max_h1_in == 0) then
                        max_h1_in = 0
                        max_k1_in = 0
                        max_l1_in = 0
                    else
                        write(*,*) 'ERROR: Wrong input in line 19'
                        stop
                    end if
                end if
            else if (i == 23) then
                read(1, *) sym_stat
            else if (i == 24) then
                read(1, *) sym_e
            else if (i == 25) then
                read(1, *) max_values(1), max_values(2), max_values(3), &
                          max_values(4), max_values(5), max_values(6)
            else if (i == 26) then
                read(1, *) min_values(1), min_values(2), min_values(3), &
                          min_values(4), min_values(5), min_values(6)
            else if (i == 27) then
                read(1, *) tilt_check
            else if (i == 28) then
                read(1, *) fixhklfile
            else
                read(1, *)
            end if
        end do
        
        close(1)
        
        if (abs(max_values(4) - min_values(4)) < 0.01d0 .and. &
            abs(max_values(5) - min_values(5)) < 0.01d0 .and &
            abs(max_values(6) - min_values(6)) < 0.01d0) then
            crystal_system = 1
        else
            crystal_system = 0
        end if
        
    end subroutine
    
    subroutine read_diffraction_data(filename_dif, diffraction_num)
        character(len=512), intent(in) :: filename_dif
        integer, intent(out) :: diffraction_num
        
        character(len=80) :: c80tmp
        integer :: ierror
        
        open(10, file=filename_dif, status="old")
        diffraction_num = 0
        max_q = 0.0d0
        
        do while (.true.)
            read(10, "(a)", iostat=ierror) c80tmp
            if (c80tmp == " " .or. ierror /= 0) exit
            diffraction_num = diffraction_num + 1
            read(c80tmp, *) value1(diffraction_num), value(diffraction_num), &
                          contribution(diffraction_num)
            if (value1(diffraction_num) > max_q) then
                max_q = value1(diffraction_num)
            end if
        end do
        
        close(10)
        
    end subroutine
    
    subroutine read_fixed_hkl_file()
        integer :: i
        
        if (fixhklfile > 0) then
            allocate(fixhkl(fixhklfile, 4))
            open(11, file="fixhkl.txt", status="old")
            do i = 1, fixhklfile
                read(11, *) fixhkl(i,1), fixhkl(i,2), fixhkl(i,3), fixhkl(i,4)
            end do
            close(11)
        end if
        
    end subroutine

end module io_module
