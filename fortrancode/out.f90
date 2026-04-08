module fitting_module
    integer,parameter :: maxdata=1000
    real*8 x(maxdata),value(maxdata),value1(maxdata)
    real*8 e2,e3,e4,wavelength,x1,sym_e,sym_cal
    real*8 Miller_trans(maxdata,7)
    integer sym_stat
    integer level
    integer tilt_check
    integer :: fixhklfile!是否存在固定文件
    integer,allocatable :: fixhkl(:,:)
    integer :: max_h1_in, max_k1_in, max_l1_in  ! 用户输入的Miller指数限制
    integer :: max_h1, max_k1, max_l1  ! 实际使用的Miller指数限制（全局变量）
    integer :: h_user_set, k_user_set, l_user_set  ! 用户设置标志
    real*8 :: max_q  ! 最大q值
    integer :: max_h1_by_cell, max_k1_by_cell, max_l1_by_cell  ! 基于晶胞参数的Miller指数（整数）
    integer :: max_h1_by_q, max_k1_by_q, max_l1_by_q  ! 基于q值的Miller指数（整数）
    real*8 :: max_values(6),min_values(6)
end module


module calhkl
    use fitting_module
    implicit none
contains
    !==========================================================================
    !==========================================================================
    !**************************************************************************
    subroutine error_cal_initial(diffraction_num, parm)
        !修改说明：
        !1. Miller指数限制已移至主程序计算，使用全局变量max_h1, max_k1, max_l1
        !2. 重构算法：边计算边比较边记录，避免存储无用数据，大幅降低内存占用
        !3. 优化逻辑：每个实验衍射点独立寻找最佳匹配晶面，无需预存所有计算结果

        integer, intent(in) :: diffraction_num
        real(kind=8), intent(inout) :: parm(:)

        !内部变量
        integer :: a1, b1, c1  !当前遍历的Miller指数
        integer :: k, l, n     !循环变量
        integer :: num_ref     !最佳匹配位置记录
        integer :: valid_count !有效计算点计数器
        integer :: i

        real(kind=8) :: a, b, c, alpha, beta, gamma
        real(kind=8) :: V
        real(kind=8) :: A11, B11, C11, D11, E11, F11
        real(kind=8) :: theta, d, q, PHI, d1, y1, phi_root
        real(kind=8), parameter :: pi = 3.14159265358979323846
        real(kind=8) :: tilt_angle, PHI_asin, PHIobs
        real(kind=8) :: error_lowest, error_mid

        !中间计算变量（无需大数组存储）
        real(kind=8) :: current_q, current_PHI_or_y1, current_theta
        integer :: current_h, current_k, current_l
        real(kind=8) :: current_V
        real(kind=8), allocatable :: min_error_list(:)

        character(len=512) :: filename1,filename2,filename3,filename_5,filename_6!定义文件名
        
        filename_6="FullMiller.txt"
        open(unit=6,file=filename_6,status='unknown',action='write')!打开cell_n文件,并且将优化后的晶胞参数写入到5号文件中

        write(6,*)"H K L q(A-1) psi(degree) psi-root(degree) 2theta(degree)"

        !初始化
        tilt_angle = 0.0d0
        if (tilt_check == 1) then
            tilt_angle = parm(7) * pi / 180
        end if

        !读取晶胞参数
        a = parm(1)
        b = parm(2)
        c = parm(3)

        !处理a*与b*垂直约束
        ! if (ortho_ab_star == 1) then
        !     alpha = parm(4) * pi / 180
        !     beta = parm(5) * pi / 180
        !     gamma = acos(cos(alpha) * cos(beta))
        !     parm(6) = gamma * 180 / pi
        ! else if (crystal_system == 1) then
        !     alpha = pi / 2
        !     beta = pi / 2
        !     gamma = pi / 2
        ! else
        alpha = parm(4) * pi / 180
        beta = parm(5) * pi / 180
        gamma = parm(6) * pi / 180
        ! end if

        V = a * b * c * (1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + 2 * cos(alpha) * cos(beta) * cos(gamma))**0.5
        if (isnan(V) .or. V < 0.01) then
            V = 10000000
        end if

        !计算晶面参数
        A11 = b**2 * c**2 * sin(alpha)**2
        B11 = a**2 * c**2 * sin(beta)**2
        C11 = a**2 * b**2 * sin(gamma)**2
        D11 = a * b * c**2 * (cos(alpha) * cos(beta) - cos(gamma))
        E11 = a**2 * b * c * (cos(beta) * cos(gamma) - cos(alpha))
        F11 = a * b**2 * c * (cos(gamma) * cos(alpha) - cos(beta))

        !Miller指数限制已在主程序中计算完毕，直接使用全局变量max_h1, max_k1, max_l1
        max_h1 = 10
        max_l1 = 30
        max_k1 = 10
        ! ---------------------------------------

        ! 1. 初始化部分
        ! 为每个实验点分配一个最小误差记录变量
        if (allocated(min_error_list)) deallocate(min_error_list)
        allocate(min_error_list(diffraction_num))
        
        ! 初始化误差为无穷大，初始化 Miller_trans 为默认值 (1,0,0)
        min_error_list = 1.0d10
        Miller_trans(:, 1) = 1
        Miller_trans(:, 2) = 0
        Miller_trans(:, 3) = 0

        current_V = V ! 记录当前体积

        ! 2. 外层循环：遍历理论晶面 (h, k, l)
        ! 将计算量大的部分放在外层，确保每组 hkl 只计算一次物理量
        do c1 = 0, max_l1
            
            if (c1 == 0) then
                y1 = 0.0d0
            else
                y1 = real(c1) / c
            end if

            do b1 = -max_k1, max_k1
                do a1 = -max_h1, max_h1

                    ! --- [公共计算模块 START] ---
                    ! 这些计算不再依赖 k，因此针对每个 hkl 只算一次

                    ! 跳过无意义晶面
                    if (a1 == 0 .and. b1 == 0 .and. c1 == 0) cycle

                    ! 计算 d 间距 (耗时操作)
                    d = 1.0d0 / sqrt((A11 * a1**2 + B11 * b1**2 + C11 * c1**2 + &
                                     2 * D11 * a1 * b1 + 2 * E11 * b1 * c1 + &
                                     2 * F11 * a1 * c1) / V**2)

                    ! 计算 theta
                    theta = asin(wavelength / (2.0d0 * d))

                    ! 检查 theta 有效性 (NaN check)
                    if (theta /= theta) cycle 

                    ! 计算 q 值
                    q = 1.0d0 / d * 2.0d0 * pi

                    ! 计算方位角 PHI
                    d1 = 1.0d0 / wavelength * sin(2.0d0 * theta)

                    ! 
                    PHI_asin = (y1 / cos(tilt_angle) + 1.0d0 / d * sin(theta) * tan(tilt_angle)) / d1
                    if (PHI_asin > 1.0d0 .or. PHI_asin < -1.0d0) then
                        PHIobs = pi / 2.0d0
                    else
                        PHIobs = asin(PHI_asin)
                    end if
                    ! else
                    if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
                        PHI = pi / 2.0d0
                    else
                        PHI = asin(y1 / d1)
                    end if
                    ! end if
                    ! --- [公共计算模块 END] ---


                    ! write(6,*)"H K L q(A-1) psi(degree) psi-root(degree) 2theta(degree)"
                    if (PHI * 180.0d0 / pi < -99.0d0 .or. q > 6.0d0) then
                        cycle
                    else
                        write(6,*) a1,b1,c1,q,PHIobs*180/pi,&
                        &PHI*180/pi,theta*2*180/pi
                    end if

                    phi_root = PHI
                    if (tilt_check == 1) then
                        PHI=PHIobs
                    end if

                    ! 3. 内层循环：遍历实验衍射点
                    ! 将当前计算好的 (q, PHI) 与所有实验点进行比较
                    do k = 1, diffraction_num
                        
                        ! 计算误差
                        if (level == 1) then
                            error_mid = abs(q - value1(k)) * e3 + abs(PHI * 180.0d0 / pi - value(k)) * e2
                        else if (level == 2) then
                            error_mid = abs(q - value1(k)) * e3 + abs(y1 - value(k)) * e2
                        end if

                        ! 核心逻辑：如果当前 hkl 对第 k 个点的误差比之前的更小，则更新记录
                        if (error_mid < min_error_list(k)) then
                            min_error_list(k) = error_mid
                            Miller_trans(k, 1) = a1
                            Miller_trans(k, 2) = b1
                            Miller_trans(k, 3) = c1
                            Miller_trans(k, 4) = q
                            Miller_trans(k, 5) = PHI
                            Miller_trans(k, 6) = phi_root
                            Miller_trans(k, 7) = current_V
                        end if

                    end do ! 结束实验点遍历

                    
                end do ! a1
            end do ! b1
        end do ! c1

        ! 释放临时数组
        if (allocated(min_error_list)) deallocate(min_error_list)
        
        close(6)

        return

    end subroutine error_cal_initial


end module calhkl

program LMfit
    use fitting_module
    use calhkl
    implicit real*8 (a-h,o-z)
    integer :: nparm
    integer :: diffraction_num,num_cell
    real*8,allocatable :: parm(:) !a,b,c,alpha,beta,gamma
    real*8 fiterr(maxdata),fitval(maxdata),fitval1(maxdata)
    character(len=512) :: filename_input,filename_cell,filename_dif,input_type,input_type2,input_type3
    character(len=512) :: filename1,filename2,filename3,filename_5,filename_6!定义文件名
    real*8,allocatable :: cell_parameter(:,:),error_total(:)
    character c80tmp*80
    real*8 :: tilt_angle
    real*8 , allocatable :: reflection_position(:,:), reflection_position1(:,:)

    
    tol=1D-7!收敛限
    maxcall=5000!最大步长

    !-----------------------------------------------------代码输入部分-----------------------------------------------
    !读取cell_n.txt文件中的数据，
    !读取时候需要程序从后续-中的内容读取，然后将其赋值给filename_cell
    call get_command_argument(1,input_type)
    call get_command_argument(2,filename1)
    call get_command_argument(3,input_type2)
    call get_command_argument(4,filename2)
    call get_command_argument(5,input_type3)
    call get_command_argument(6,filename3)

    !write(*,*) 'test-begin'

    !如果检测到是input_type是-i，-input，则从2中读取filename1,给filename_input赋值,如果是-c，-crystal，则从4中读取filename2,给filename_input赋值
    !-d是检测器所的实验数据，-detector
    !
    if (input_type=='-i' .or. input_type=='-input') then
        filename_input=filename1
        if (input_type2=='-c' .or. input_type2=='-crystal') then
            filename_cell=filename2
            filename_dif=filename3
        else if (input_type2=='-d' .or. input_type2=='-diffrac') then
            filename_dif=filename2
            filename_cell=filename3
        end if
    else if (input_type=='-c' .or. input_type=='-crystal') then
        filename_cell=filename1
        if (input_type2=='-i' .or. input_type2=='-input') then
            filename_input=filename2
            filename_dif=filename3
        else if (input_type2=='-d' .or. input_type2=='-diffrac') then
            filename_dif=filename2
            filename_input=filename3
        end if
    else if (input_type=='-d' .or. input_type=='-diffrac') then
        filename_dif=filename1
        if (input_type2=='-i' .or. input_type2=='-input') then
            filename_input=filename2
            filename_cell=filename3
        else if (input_type2=='-c' .or. input_type2=='-crystal') then
            filename_cell=filename2
            filename_input=filename3
        end if
    else
        write(*,*) 'wrong input_type，choosen -i,-input,-c,-crystal,-d,-diffrac'
        stop
    end if

    !----------------------------------------命令行输入结束---------------------------------------
    !---------------------------------------------------INPUT文件读取部分-----------------------------------------------    
    !读取cell_n.txt文件中的数据
    open(unit=1,file=filename_input,status='old',action='read')!打开input文件,并且将文件的内容读取到1号文件中
    !文件第一行为波长，第二行为检测器距离，第三行为检测器类型
    do i=1,28
        if (i==1) then
            read(1,*) wavelength
        ! else if (i==4) then
        !     read(1,*) num_cell!读取晶胞数目
        else if (i==13) then
            read(1,*) level!读取层次,1是q-psi,2是theta模式
        else if (i==15) then
            read(1,*) e2
        else if (i==16) then
            read(1,*) e3
        else if (i==17) then
            !打印这一行的所有内容
            read(1,*) e4
        else if (i==18) then
            read(1,*) x1
        else if (i==23) then
            read(1,*) sym_stat
        else if (i==24) then
            read(1,*) sym_e
        else if (i==27) then
            read(1,*) tilt_check!确定是否优化tilt-0等默认不优化，1为优化
            ! print*,tilt_check
        ! else if (i==19) then

        !     ! read(1,*) max_h1_in, max_k1_in, max_l1_in  !读取用户设定的Miller指数限制
        !     read(1, '(A)') buffer
        !     read(buffer, *, iostat=io_status) max_h1_in, max_k1_in, max_l1_in
        !     ! 3. 检查读取状态
        !     if (io_status /= 0) then
        !         ! 如果读取 3 个数失败（io_status不为0），说明输入不足3个
        !         ! 尝试只读取第 1 个数
        !         read(buffer, *, iostat=io_status) max_h1_in
        !         ! 如果读取 1 个数成功，且该数为 0
        !         if (io_status == 0 .and. max_h1_in == 0) then
        !             ! 用户输入了单个 0，触发“默认逻辑”
        !             max_h1_in = 0
        !             max_k1_in = 0
        !             max_l1_in = 0
        !         else
        !             ! 既不是3个数，也不是单个0，说明格式真的错了
        !             write(*,*) 'ERROR: Wrong input in line 19'
        !             stop
        !         end if
        !     end if        

        else
            read(1,*)
        end if 
    end do

    num_cell=1
    close(1)!关闭文件
    
    ! if (diffraction_num>=1000) then
    !     write(*,*) 'MAX_diffraction peaks over 1000'
    !     stop
    ! end if 
    !==============================================================

    !==============================衍射文件=======================
    open(10,file=filename_dif,status="old")!打开文件！
    diffraction_num=0!数据点数目
    do while(.true.)
        read(10,"(a)",iostat=ierror) c80tmp!防错装置
        if (c80tmp==" ".or.ierror/=0) exit
        diffraction_num=diffraction_num+1
        read(c80tmp,*) value1(diffraction_num),value(diffraction_num)!value1-q,value-phi
    end do
    close(10)

    !write(*,"(i6,' data have been loaded')") diffraction_num

    


    !====================晶胞参数文件=======================
    open(unit=2,file=filename_cell,status='old',action='read')!打开cell_n文件,并且将文件的内容读取到2号文件中
    !读取每一行的数据，然后将其赋值给cell_parameter
    

    do i=1,num_cell
        if (tilt_check == 1) then
            allocate(cell_parameter(num_cell,7))
            read(2,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6),cell_parameter(i,7)
            nparm = 7
        else
            allocate(cell_parameter(num_cell,6))
            read(2,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6)
            nparm = 6
        end if
    end do
    close(2)!关闭文件
    !====================================================

    allocate(error_total(num_cell))
    allocate(parm(nparm))
    allocate(reflection_position(10000,5))
    allocate(reflection_position1(10000,6))
    !读取parm


    do i=1,num_cell
        parm(1)=cell_parameter(i,1)
        parm(2)=cell_parameter(i,2)
        parm(3)=cell_parameter(i,3)
        parm(4)=cell_parameter(i,4)
        parm(5)=cell_parameter(i,5)
        parm(6)=cell_parameter(i,6)
        if (tilt_check == 1) then
            parm(7)=cell_parameter(i,7)
            ! print*, "READ",cell_parameter(i,7)
        end if

        !寻找miller指数

        call error_cal_initial(diffraction_num,parm)!,reflection_position,reflection_position1)

    end do

    filename_5="outputMiller.txt"
    open(unit=5,file=filename_5,status='unknown',action='write')!打开cell_n文件,并且将优化后的晶胞参数写入到5号文件中

    if (tilt_check == 1) then
        write(5,*)"H K L q psi psi-root"
        do i=1,diffraction_num
            write(5,*) Miller_trans(i,1),Miller_trans(i,2),Miller_trans(i,3),Miller_trans(i,4),&
                       Miller_trans(i,5)*180/3.141592653589, Miller_trans(i,6)*180/3.141592653589
        end do
        write(5,*) "volume:",Miller_trans(1,7)
    else
        write(5,*)"H K L q psi"
        do i=1,diffraction_num
            write(5,*) Miller_trans(i,1),Miller_trans(i,2),Miller_trans(i,3),Miller_trans(i,4),Miller_trans(i,5)*180/3.141592653589
        end do
        write(5,*) "volume:",Miller_trans(1,6)
    end if
    
    close(5)!关闭文件
    write(*,*) " "


    

end program
 
