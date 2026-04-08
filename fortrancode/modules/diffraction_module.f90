!##############################################################################
!#
!# @模块名称: diffraction_module (衍射计算模块)
!#
!# @功能描述: 
!#   本模块提供X射线衍射相关的数学计算功能，类似于Python中的类(Class)。
!#   包含d间距、q值、theta角、phi角、方位角等计算功能。
!#
!# @主要功能:
!#   - 计算晶面间距 d
!#   - 计算散射矢量 q
!#   - 计算Bragg角 theta
!#   - 计算方位角 PHI
!#   - 计算 y1 值
!#   - 处理tilt角度修正
!#
!# @使用说明:
!#   use diffraction_module
!#   call calculate_d_spacing(h, k, l, A11, B11, C11, D11, E11, F11, V, d)
!#   call calculate_q(d, q)
!#   call calculate_theta(wavelength, d, theta)
!#
!##############################################################################

module diffraction_module
    use fitting_module
    implicit none
    
    ! 模块内部常量
    real*8, parameter :: PI = 3.14159265358979323846d0
    
    !======================================================================
    ! @接口: calculate_d_spacing
    ! @功能: 根据Miller指数和晶胞参数计算晶面间距
    !======================================================================
    interface calculate_d_spacing
        module procedure calculate_d_spacing_direct
    end interface
    
    !======================================================================
    ! @接口: calculate_q
    ! @功能: 根据d间距计算散射矢量q
    !======================================================================
    interface calculate_q
        module procedure calculate_q_from_d
    end interface
    
    !======================================================================
    ! @接口: calculate_theta
    ! @功能: 根据波长和d间距计算Bragg角
    !======================================================================
    interface calculate_theta
        module procedure calculate_theta_from_d
    end interface
    
    !======================================================================
    ! @接口: calculate_phi
    ! @功能: 计算方位角PHI
    !======================================================================
    interface calculate_phi
        module procedure calculate_phi_with_tilt
        module procedure calculate_phi_without_tilt
    end interface

contains

    !======================================================================
    ! @子程序: calculate_d_spacing_direct
    ! @描述: 计算晶面间距 d
    !         d = 1 / sqrt((A11*h^2 + B11*k^2 + C11*l^2 + 
    !                       2*D11*h*k + 2*E11*k*l + 2*F11*h*l) / V^2)
    !======================================================================
    subroutine calculate_d_spacing_direct(h, k, l, A11, B11, C11, D11, E11, F11, V, d)
        integer, intent(in) :: h, k, l
        real*8, intent(in) :: A11, B11, C11, D11, E11, F11, V
        real*8, intent(out) :: d
        
        real*8 :: numerator
        real*8 :: denominator
        
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
    
    !======================================================================
    ! @子程序: calculate_q_from_d
    ! @描述: 计算散射矢量 q = 2*pi/d
    !======================================================================
    subroutine calculate_q_from_d(d, q)
        real*8, intent(in) :: d
        real*8, intent(out) :: q
        
        if (d > 0.0d0) then
            q = 2.0d0 * PI / d
        else
            q = 0.0d0
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_theta_from_d
    ! @描述: 计算Bragg角 theta = arcsin(lambda / 2d)
    !======================================================================
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
    
    !======================================================================
    ! @子程序: calculate_d1
    ! @描述: 计算辅助参数 d1 = sqrt(4*d^2 - lambda^2) / (2*d^2)
    !======================================================================
    subroutine calculate_d1(wavelength, d, d1)
        real*8, intent(in) :: wavelength, d
        real*8, intent(out) :: d1
        
        if (d > 0.0d0) then
            d1 = sqrt(4.0d0 * d**2 - wavelength**2) / (2.0d0 * d**2)
        else
            d1 = 0.0d0
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_y1
    ! @描述: 计算y1值（与c轴Miller指数相关）
    !        y1 = l/c (当l != 0时)
    !        y1 = 0   (当l == 0时)
    !======================================================================
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
    
    !======================================================================
    ! @子程序: calculate_phi_with_tilt
    ! @描述: 计算带tilt修正的方位角PHI
    !        考虑样品倾斜对衍射几何的影响
    !======================================================================
    subroutine calculate_phi_with_tilt(y1, d, d1, theta, tilt_angle, PHI)
        real*8, intent(in) :: y1, d, d1, theta, tilt_angle
        real*8, intent(out) :: PHI
        
        real*8 :: PHI_asin
        real*8 :: cos_tilt, tan_tilt
        
        cos_tilt = cos(tilt_angle)
        tan_tilt = tan(tilt_angle)
        
        ! PHI_asin = (y1/cos(tilt) + (1/d)*sin(theta)*tan(tilt)) / d1
        PHI_asin = (y1 / cos_tilt + (1.0d0 / d) * sin(theta) * tan_tilt) / d1
        
        if (PHI_asin > 1.0d0 .or. PHI_asin < -1.0d0) then
            PHI = PI / 2.0d0
        else
            PHI = asin(PHI_asin)
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_phi_without_tilt
    ! @描述: 计算不带tilt修正的方位角PHI
    !======================================================================
    subroutine calculate_phi_without_tilt(y1, d1, PHI)
        real*8, intent(in) :: y1, d1
        real*8, intent(out) :: PHI
        
        if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
            PHI = PI / 2.0d0
        else
            PHI = asin(y1 / d1)
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_diffraction_parameters
    ! @描述: 一站式计算衍射参数（d, q, theta, phi, y1, d1）
    !======================================================================
    subroutine calculate_diffraction_parameters(h, k, l, c, wavelength, &
                                               A11, B11, C11, D11, E11, F11, V, &
                                               tilt_angle, &
                                               d, theta, q, y1, d1, PHI)
        integer, intent(in) :: h, k, l
        real*8, intent(in) :: c, wavelength
        real*8, intent(in) :: A11, B11, C11, D11, E11, F11, V, tilt_angle
        real*8, intent(out) :: d, theta, q, y1, d1, PHI
        
        call calculate_d_spacing_direct(h, k, l, A11, B11, C11, D11, E11, F11, V, d)
        call calculate_theta_from_d(wavelength, d, theta)
        call calculate_q_from_d(d, q)
        call calculate_y1(l, c, y1)
        call calculate_d1(wavelength, d, d1)
        
        if (tilt_check == 1) then
            call calculate_phi_with_tilt(y1, d, d1, theta, tilt_angle, PHI)
        else
            call calculate_phi_without_tilt(y1, d1, PHI)
        end if
    end subroutine
    
    !======================================================================
    ! @函数: check_theta_validity
    ! @描述: 检查theta角是否有效（非NaN）
    !======================================================================
    function check_theta_validity(theta) result(is_valid)
        real*8, intent(in) :: theta
        logical :: is_valid
        
        is_valid = (theta == theta)
    end function
    
    !======================================================================
    ! @子程序: validate_d_spacing
    ! @描述: 验证d间距是否有效
    !======================================================================
    subroutine validate_d_spacing(d)
        real*8, intent(inout) :: d
        
        if (d <= 0.0d0 .or. d /= d) then
            d = 0.0d0
        end if
    end subroutine

end module diffraction_module
