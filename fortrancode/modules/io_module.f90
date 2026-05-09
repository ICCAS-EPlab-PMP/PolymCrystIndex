!##############################################################################
!#
!# @模块名称: io_module (输入输出模块)
!#
!# @功能描述: 
!#   本模块处理所有文件输入输出操作，类似于Python中的类(Class)。
!#   包含读取输入文件、衍射数据、晶胞参数，以及写入结果文件等功能。
!#
!# @主要功能:
!#   - 解析命令行参数
!#   - 读取输入配置文件
!#   - 读取衍射数据
!#   - 读取晶胞参数
!#   - 读取固定hkl文件
!#   - 写入优化结果
!#   - 打印软件信息和引用
!#
!# @使用说明:
!#   use io_module
!#   call parse_command_arguments(argc, argv, ...)
!#   call read_input_file(filename_input)
!#   call read_diffraction_data(filename_dif, diffraction_num)
!#   call read_cell_parameters(filename_cell, cell_parameter, num_cell)
!#
!##############################################################################

module io_module
    use fitting_module
    implicit none
    
    ! 模块内部常量
    real*8, parameter :: PI = 3.14159265358979323846d0
    
contains

    !======================================================================
    ! @子程序: parse_command_arguments
    ! @描述: 解析命令行参数，支持多种组合顺序
    !        
    ! @支持格式:
    !   program -i input.txt -c cell.txt -d diffraction.txt
    !   program -c cell.txt -i input.txt -d diffraction.txt
    !   program -d diffraction.txt -i input.txt -c cell.txt
    !======================================================================
    subroutine parse_command_arguments(input_type, filename1, input_type2, &
                                       filename2, input_type3, filename3, &
                                       filename_input, filename_cell, filename_dif)
        character(len=100), intent(out) :: input_type, filename1, input_type2, &
                                          filename2, input_type3, filename3
        character(len=100), intent(out) :: filename_input, filename_cell, filename_dif
        
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
    
    !======================================================================
    ! @子程序: print_usage_error
    ! @描述: 打印软件信息和错误使用提示
    !======================================================================
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
        write(*,*) " "
        write(*,*) " Jorge More, Danny Sorenson, Burton Garbow, Kenneth Hillstrom,"
        write(*,*) " The MINPACK Project,"
        write(*,*) " in Sources and Development of Mathematical Software,"
        write(*,*) " edited by Wayne Cowell,"
        write(*,*) " Prentice-Hall, 1984,"
        write(*,*) " ISBN: 0-13-823501-5,"
        write(*,*) " LC: QA76.95.S68."
        write(*,*) " "
        write(*,*) " Additionally, please CITE the following paper for this work:"
        write(*,*) " "
        write(*,*) " Ma, T., Hu, W., Wang, D. & Liu, G. (2025)."
        write(*,*) " A global optimization approach to automated indexing"
        write(*,*) " of fiber diffraction patterns. J. Appl. Cryst. 58."
        write(*,*) "----------------------------------------------------------------------"
        
        read(*,*)
        stop 'Wrong Input_type!!, choosen -i,-input,-c,-crystal,-d,-diffrac'
    end subroutine
    
    !======================================================================
    ! @子程序: read_input_file
    ! @描述: 读取输入配置文件（input.txt）
    !        
    ! @文件格式（29行）:
    !   1: wavelength
    !   4: num_cell
    !   13: level
    !   14: ortho_ab_star
    !   15: e2
    !   16: e3
    !   17: e4
    !   18: x1
    !   19: max_h1_in, max_k1_in, max_l1_in (Miller指数限制)
    !   23: sym_stat
    !   24: sym_e
    !   25: amin, bmin, cmin, alphamin, betamin, gammamin
    !   26: amax, bmax, cmax, alphamax, betamax, gammamax
    !   27: tilt_check
    !   28: fixhklfile
    !   29: fixlmode
    !======================================================================
    subroutine read_input_file(filename_input)
        character(len=100), intent(in) :: filename_input
        
        character(len=256) :: buffer
        integer :: io_status
        integer :: i
        
        open(unit=1, file=filename_input, status='old', action='read')
        
        fixhklfile = 0
        fixlmode = 0
        ortho_ab_star = 0
        
        do i = 1, 29
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
                read(1, *) amin, bmin, cmin, alphamin, betamin, gammamin
            else if (i == 26) then
                read(1, *) amax, bmax, cmax, alphamax, betamax, gammamax
            else if (i == 27) then
                read(1, *) tilt_check
            else if (i == 28) then
                read(1, *) fixhklfile
            else if (i == 29) then
                read(1, *) fixlmode
            else
                read(1, *)
            end if
        end do
        
        close(1)
        
        call update_parameter_bounds()
        call check_crystal_system_type()
        
    end subroutine
    
    !======================================================================
    ! @子程序: update_parameter_bounds
    ! @描述: 更新参数边界数组
    !======================================================================
    subroutine update_parameter_bounds()
        max_values(1) = amax
        max_values(2) = bmax
        max_values(3) = cmax
        max_values(4) = alphamax
        max_values(5) = betamax
        max_values(6) = gammamax
        
        min_values(1) = amin
        min_values(2) = bmin
        min_values(3) = cmin
        min_values(4) = alphamin
        min_values(5) = betamin
        min_values(6) = gammamin
    end subroutine
    
    !======================================================================
    ! @子程序: check_crystal_system_type
    ! @描述: 检查晶体系统类型
    !======================================================================
    subroutine check_crystal_system_type()
        if (abs(alphamax - alphamin) < 0.01d0 .and. &
            abs(betamax - betamin) < 0.01d0 .and &
            abs(gammamax - gammamin) < 0.01d0) then
            crystal_system = 1
        else
            crystal_system = 0
        end if
    end subroutine
    
    !======================================================================
    ! @子程序: read_diffraction_data
    ! @描述: 读取衍射数据文件
    !        
    ! @文件格式:
    !   每行: value1 (q), value (phi/y1), contribution (权重)
    !======================================================================
    subroutine read_diffraction_data(filename_dif, diffraction_num)
        character(len=100), intent(in) :: filename_dif
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
    
    !======================================================================
    ! @子程序: read_cell_parameters
    ! @描述: 读取晶胞参数文件
    !======================================================================
    subroutine read_cell_parameters(filename_cell, cell_parameter, num_cell)
        character(len=100), intent(in) :: filename_cell
        real*8, allocatable, intent(out) :: cell_parameter(:,:)
        integer, intent(in) :: num_cell
        
        integer :: nparm
        integer :: i
        
        open(unit=2, file=filename_cell, status='old', action='read')
        
        if (tilt_check == 1) then
            allocate(cell_parameter(num_cell, 7))
            nparm = 7
        else
            allocate(cell_parameter(num_cell, 6))
            nparm = 6
        end if
        
        if (tilt_check == 1) then
            do i = 1, num_cell
                read(2, *) cell_parameter(i,1), cell_parameter(i,2), cell_parameter(i,3), &
                          cell_parameter(i,4), cell_parameter(i,5), cell_parameter(i,6), &
                          cell_parameter(i,7)
            end do
        else
            do i = 1, num_cell
                read(2, *) cell_parameter(i,1), cell_parameter(i,2), cell_parameter(i,3), &
                          cell_parameter(i,4), cell_parameter(i,5), cell_parameter(i,6)
            end do
        end if
        
        close(2)
        
    end subroutine
    
    !======================================================================
    ! @子程序: read_fixed_hkl_file
    ! @描述: 读取固定hkl文件
    !======================================================================
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
    
    !======================================================================
    ! @子程序: write_results
    ! @描述: 写入优化结果到文件
    !======================================================================
    subroutine write_results(cell_parameter, num_cell, error_total, filename_cell)
        real*8, intent(in) :: cell_parameter(:,:)
        real*8, intent(in) :: error_total(:)
        character(len=100), intent(in) :: filename_cell
        
        character(len=100) :: filename_5
        integer :: i
        
        open(unit=4, file='diffraction.txt', status='unknown', action='write')
        do i = 1, num_cell
            write(4, *) error_total(i)
        end do
        close(4)
        
        filename_5 = filename_cell(1:len_trim(filename_cell) - 4) // '_annealing.txt'
        
        open(unit=5, file=filename_5, status='unknown', action='write')
        do i = 1, num_cell
            if (tilt_check == 1) then
                write(5, *) cell_parameter(i,1), cell_parameter(i,2), cell_parameter(i,3), &
                           cell_parameter(i,4), cell_parameter(i,5), cell_parameter(i,6), &
                           cell_parameter(i,7)
            else
                write(5, *) cell_parameter(i,1), cell_parameter(i,2), cell_parameter(i,3), &
                           cell_parameter(i,4), cell_parameter(i,5), cell_parameter(i,6)
            end if
        end do
        close(5)
        
    end subroutine
    
    !======================================================================
    ! @子程序: print_optimization_complete
    ! @描述: 打印优化完成信息
    !======================================================================
    subroutine print_optimization_complete()
        if (ortho_ab_star == 1) then
            write(*,*) "Optimization completed with a* ? b* constraint enabled."
            write(*,*) "Gamma angle was calculated from alpha and beta using: &
                       &gamma = arccos(cos(alpha)*cos(beta))"
        else
            write(*,*) "Optimization completed."
        end if
        write(*,*) " "
    end subroutine
    
    !======================================================================
    ! @子程序: print_constraint_warning
    ! @描述: 打印约束冲突警告
    !======================================================================
    subroutine print_constraint_warning()
        if (ortho_ab_star == 1 .and. crystal_system == 1) then
            write(*,*) 'Warning: Both ortho_ab_star and crystal_system constraints are enabled.'
            write(*,*) 'The ortho_ab_star constraint will take precedence.'
        end if
    end subroutine

end module io_module
