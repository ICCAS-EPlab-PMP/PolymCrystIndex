!##############################################################################
!#
!# @程序名称: LMfit (Levenberg-Marquardt纤维衍射拟合程序)
!#
!# @功能描述: 
!#   本程序是纤维衍射图案全自动标定和晶胞参数优化主程序。
!#   使用MINPACK库实现的Levenberg-Marquardt算法进行非线性最小二乘拟合。
!#
!# @版本历史:
!#   VERSION 1.0  - 最终基础版本内容
!#   VERSION 1.1  - 网页版正式上线
!#   VERSION 1.2  - 2025.6.12 - tilt模块开发
!#   VERSION 1.21 - 2025.6.20 - tilt梯度修正
!#   VERSION 1.3  - 2025.7.22 - 固定晶面功能
!#   VERSION 1.4  - 2025.10.13 - a*与b*垂直优化
!#   VERSION 1.5  - 2026.1.2  - 晶胞参数限制增强
!#   VERSION 1.51 - 2026.1.29 - 多核并行化
!#
!# @使用方法:
!#   ./LMfit -i input.txt -c cell.txt -d diffraction.txt
!#   ./LMfit -c cell.txt -i input.txt -d diffraction.txt
!#   ./LMfit -d diffraction.txt -i input.txt -c cell.txt
!#
!# @输入文件:
!#   input.txt     - 配置文件（波长、参数权重、约束等）
!#   cell.txt      - 晶胞参数初始值
!#   diffraction.txt - 衍射数据（q, phi, contribution）
!#   fixhkl.txt    - 固定晶面列表（可选）
!#
!# @输出文件:
!#   diffraction.txt     - 各晶胞的总误差
!#   cell_annealing.txt  - 优化后的晶胞参数
!#
!##############################################################################

program LMfit
    use fitting_module
    use crystal_module
    use diffraction_module
    use miller_module
    use error_module
    use minpack_module
    use io_module
    implicit real*8 (a-h, o-z)
    
    !======================================================================
    ! 程序变量声明
    !======================================================================
    integer :: nparm
    integer :: diffraction_num
    real*8, allocatable :: parm(:)
    real*8 fiterr(maxdata), fitval(maxdata), fitval1(maxdata)
    
    character(len=100) :: filename_input, filename_cell, filename_dif
    character(len=100) :: filename1, filename2, filename3
    character(len=100) :: input_type, input_type2, input_type3
    
    real*8, allocatable :: cell_parameter(:,:), error_total(:)
    
    real*8 :: tol
    integer :: maxcall, info
    integer :: i, j
    
    !======================================================================
    ! 优化参数设置
    !======================================================================
    tol = 1.0d-7
    maxcall = 5000
    
    !======================================================================
    ! 命令行参数解析
    !======================================================================
    call parse_command_arguments(input_type, filename1, input_type2, &
                                 filename2, input_type3, filename3, &
                                 filename_input, filename_cell, filename_dif)
    
    !======================================================================
    ! 读取输入配置文件
    !======================================================================
    call read_input_file(filename_input)
    
    !======================================================================
    ! 读取衍射数据
    !======================================================================
    call read_diffraction_data(filename_dif, diffraction_num)
    
    !======================================================================
    ! 计算Miller指数限制
    !======================================================================
    h_user_set = 0
    k_user_set = 0
    l_user_set = 0
    
    if (max_h1_in > 0) h_user_set = 1
    if (max_k1_in > 0) k_user_set = 1
    if (max_l1_in > 0) l_user_set = 1
    
    call calculate_miller_limits(amax, bmax, cmax, wavelength, max_q, &
                                  h_user_set, k_user_set, l_user_set)
    
    !======================================================================
    ! 约束兼容性检查
    !======================================================================
    call print_constraint_warning()
    
    !======================================================================
    ! 读取固定hkl文件
    !======================================================================
    call read_fixed_hkl_file()
    
    !======================================================================
    ! 读取晶胞参数
    !======================================================================
    call read_cell_parameters(filename_cell, cell_parameter, num_cell)
    
    allocate(error_total(num_cell))
    
    if (tilt_check == 1) then
        nparm = 7
    else
        nparm = 6
    end if
    
    allocate(parm(nparm))
    
    !======================================================================
    ! 主优化循环
    !======================================================================
    do i = 1, num_cell
        call set_parameters_from_cell(cell_parameter, i, parm, nparm)
        
        call error_cal_initial(diffraction_num, parm)
        
        call lmdif1(calcfiterr, diffraction_num, nparm, parm, &
                   fiterr(1:diffraction_num), tol, maxcall, info)
        
        call update_cell_from_parameters(cell_parameter, i, parm, nparm)
        
        call calculate_total_error(diffraction_num, fiterr, error_total(i))
        
    end do
    
    !======================================================================
    ! 输出结果
    !======================================================================
    call write_results(cell_parameter, num_cell, error_total, filename_cell)
    
    call print_optimization_complete()
    
contains

    !======================================================================
    ! @子程序: set_parameters_from_cell
    ! @描述: 从晶胞数组设置参数向量
    !======================================================================
    subroutine set_parameters_from_cell(cell_parameter, idx, parm, nparm)
        real*8, intent(in) :: cell_parameter(:,:)
        integer, intent(in) :: idx
        real*8, intent(out) :: parm(:)
        integer, intent(out) :: nparm
        
        if (tilt_check == 1) then
            nparm = 7
            parm(1) = cell_parameter(idx, 1)
            parm(2) = cell_parameter(idx, 2)
            parm(3) = cell_parameter(idx, 3)
            parm(4) = cell_parameter(idx, 4)
            parm(5) = cell_parameter(idx, 5)
            parm(6) = cell_parameter(idx, 6)
            parm(7) = cell_parameter(idx, 7)
        else
            nparm = 6
            parm(1) = cell_parameter(idx, 1)
            parm(2) = cell_parameter(idx, 2)
            parm(3) = cell_parameter(idx, 3)
            parm(4) = cell_parameter(idx, 4)
            parm(5) = cell_parameter(idx, 5)
            parm(6) = cell_parameter(idx, 6)
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: update_cell_from_parameters
    ! @描述: 将优化后的参数更新到晶胞数组
    !======================================================================
    subroutine update_cell_from_parameters(cell_parameter, idx, parm, nparm)
        real*8, intent(inout) :: cell_parameter(:,:)
        integer, intent(in) :: idx
        real*8, intent(in) :: parm(:)
        integer, intent(in) :: nparm
        
        if (tilt_check == 1) then
            cell_parameter(idx, 1) = parm(1)
            cell_parameter(idx, 2) = parm(2)
            cell_parameter(idx, 3) = parm(3)
            cell_parameter(idx, 4) = parm(4)
            cell_parameter(idx, 5) = parm(5)
            cell_parameter(idx, 6) = parm(6)
            cell_parameter(idx, 7) = parm(7)
        else
            cell_parameter(idx, 1) = parm(1)
            cell_parameter(idx, 2) = parm(2)
            cell_parameter(idx, 3) = parm(3)
            cell_parameter(idx, 4) = parm(4)
            cell_parameter(idx, 5) = parm(5)
            cell_parameter(idx, 6) = parm(6)
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: calculate_total_error
    ! @描述: 计算总误差，处理NaN值
    !======================================================================
    subroutine calculate_total_error(diffraction_num, fiterr, total_error)
        integer, intent(in) :: diffraction_num
        real*8, intent(in) :: fiterr(diffraction_num)
        real*8, intent(out) :: total_error
        
        integer :: j
        
        total_error = 0.0d0
        do j = 1, diffraction_num
            if (isnan(fiterr(j))) then
                fiterr(j) = 100000.0d0
            end if
            total_error = total_error + fiterr(j)
        end do
    end subroutine

end program LMfit
