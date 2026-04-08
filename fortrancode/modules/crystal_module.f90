!##############################################################################
!#
!# @模块名称: crystal_module (晶体计算模块)
!#
!# @功能描述: 
!#   本模块提供晶体学相关的数学计算功能，类似于Python中的类(Class)。
!#   包含晶胞参数处理、体积计算、晶面间距计算、度与弧度转换等功能。
!#
!# @主要功能:
!#   - 晶胞参数初始化和验证
!#   - 晶体体积计算
!#   - 晶面参数(A11, B11, C11, D11, E11, F11)计算
!#   - a*与b*垂直约束处理
!#   - 角度单位转换
!#
!# @使用说明:
!#   use crystal_module
!#   call init_crystal_parameters(parm, a, b, c, alpha, beta, gamma, tilt_angle)
!#   call calculate_volume(a, b, c, alpha, beta, gamma, V)
!#   call calculate_reciprocal_parameters(...)
!#
!##############################################################################

module crystal_module
    use fitting_module
    implicit none
    
    ! 模块内部常量
    real*8, parameter :: PI = 3.14159265358979323846d0
    
    !======================================================================
    ! @接口: init_crystal_parameters
    ! @功能: 从参数数组初始化晶体参数，处理各种约束条件
    ! @输入: parm - 参数数组, nparm - 参数数量
    ! @输出: a, b, c, alpha, beta, gamma, tilt_angle
    !======================================================================
    interface init_crystal_parameters
        module procedure init_crystal_parameters_with_tilt
        module procedure init_crystal_parameters_without_tilt
    end interface
    
    !======================================================================
    ! @接口: calculate_volume
    ! @功能: 计算晶体体积
    ! @输入: a, b, c, alpha, beta, gamma (弧度)
    ! @输出: V (体积)
    !======================================================================
    interface calculate_volume
        module procedure calculate_volume_direct
    end interface
    
    !======================================================================
    ! @接口: calculate_reciprocal_parameters
    ! @功能: 计算倒易点阵参数
    !======================================================================
    interface calculate_reciprocal_parameters
        module procedure calculate_reciprocal_params
    end interface

contains

    !======================================================================
    ! @子程序: init_crystal_parameters_with_tilt
    ! @描述: 处理带tilt参数的情况
    !======================================================================
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
    
    !======================================================================
    ! @子程序: init_crystal_parameters_without_tilt
    ! @描述: 处理不带tilt参数的情况
    !======================================================================
    subroutine init_crystal_parameters_without_tilt(parm, a, b, c, alpha, beta, gamma)
        real*8, intent(in) :: parm(:)
        real*8, intent(out) :: a, b, c, alpha, beta, gamma
        
        a = parm(1)
        b = parm(2)
        c = parm(3)
        
        call calculate_crystal_angles(parm, alpha, beta, gamma)
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_crystal_angles
    ! @描述: 计算晶体角度，处理各种约束条件
    !======================================================================
    subroutine calculate_crystal_angles(parm, alpha, beta, gamma)
        real*8, intent(in) :: parm(:)
        real*8, intent(out) :: alpha, beta, gamma
        
        if (ortho_ab_star == 1) then
            ! a*与b*垂直约束：根据alpha和beta计算gamma
            alpha = parm(4) * PI / 180.0d0
            beta = parm(5) * PI / 180.0d0
            gamma = acos(cos(alpha) * cos(beta))
            ! 更新parm(6)为计算得到的gamma值
        else if (crystal_system == 1) then
            ! 正交晶体系统：所有角度为90度
            alpha = PI / 2.0d0
            beta = PI / 2.0d0
            gamma = PI / 2.0d0
        else
            ! 无约束：直接使用输入的角度
            alpha = parm(4) * PI / 180.0d0
            beta = parm(5) * PI / 180.0d0
            gamma = parm(6) * PI / 180.0d0
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_volume_direct
    ! @描述: 直接计算晶体体积
    !======================================================================
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
    
    !======================================================================
    ! @子程序: validate_volume
    ! @描述: 验证体积是否有效，无效时设置默认值
    !======================================================================
    subroutine validate_volume(V)
        real*8, intent(inout) :: V
        
        if (isnan(V) .or. V < 0.01d0) then
            V = 10000000.0d0
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_reciprocal_params
    ! @描述: 计算倒易点阵参数A11, B11, C11, D11, E11, F11
    !======================================================================
    subroutine calculate_reciprocal_params(a, b, c, alpha, beta, gamma, V, &
                                           A11, B11, C11, D11, E11, F11)
        real*8, intent(in) :: a, b, c, alpha, beta, gamma, V
        real*8, intent(out) :: A11, B11, C11, D11, E11, F11
        
        real*8 :: cos_alpha, cos_beta, cos_gamma
        real*8 :: sin_alpha
        
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
    
    !======================================================================
    ! @函数: degrees_to_radians
    ! @描述: 将角度转换为弧度
    !======================================================================
    function degrees_to_radians(degrees) result(radians)
        real*8, intent(in) :: degrees
        real*8 :: radians
        radians = degrees * PI / 180.0d0
    end function
    
    !======================================================================
    ! @函数: radians_to_degrees
    ! @描述: 将弧度转换为角度
    !======================================================================
    function radians_to_degrees(radians) result(degrees)
        real*8, intent(in) :: radians
        real*8 :: degrees
        degrees = radians * 180.0d0 / PI
    end function
    
    !======================================================================
    ! @子程序: apply_ortho_ab_star_constraint
    ! @描述: 应用a*与b*垂直约束，更新gamma值
    !======================================================================
    subroutine apply_ortho_ab_star_constraint(parm)
        real*8, intent(inout) :: parm(:)
        
        real*8 :: alpha, beta, gamma
        
        if (ortho_ab_star == 1) then
            alpha = parm(4) * PI / 180.0d0
            beta = parm(5) * PI / 180.0d0
            gamma = acos(cos(alpha) * cos(beta))
            parm(6) = gamma * 180.0d0 / PI
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: check_crystal_system
    ! @描述: 检查是否为正交晶体系统
    !======================================================================
    subroutine check_crystal_system(alphamin, alphamax, betamin, betamax, &
                                   gammamin, gammamax, is_ortho)
        real*8, intent(in) :: alphamin, alphamax, betamin, betamax, gammamin, gammamax
        integer, intent(out) :: is_ortho
        
        if (abs(alphamax - alphamin) < 0.01d0 .and. &
            abs(betamax - betamin) < 0.01d0 .and &
            abs(gammamax - gammamin) < 0.01d0) then
            is_ortho = 1
        else
            is_ortho = 0
        end if
    end subroutine

end module crystal_module
