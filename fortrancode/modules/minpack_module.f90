!##############################################################################
!#
!# @模块名称: minpack_module (MINPACK优化库模块)
!#
!# @功能描述: 
!#   本模块是MINPACK非线性优化库的接口封装，类似于Python中的类(Class)。
!#   MINPACK是最小二乘法和非线性方程求解的著名库。
!#
!# @主要功能:
!#   - Levenberg-Marquardt算法 (lmdif1)
!#   - 梯度检查 (chkder)
!#   - 狗腿法 (dogleg)
!#   - 雅可比矩阵计算 (fdjac1, fdjac2)
!#   - 混合优化方法 (hybrd, hybrj)
!#
!# @引用信息:
!#   Jorge More, Burton Garbow, Kenneth Hillstrom,
!#   User Guide for MINPACK-1,
!#   Technical Report ANL-80-74,
!#   Argonne National Laboratory, 1980.
!#
!# @使用说明:
!#   use minpack_module
!#   call lmdif1(fcn, m, n, x, fvec, tol, maxfev, info)
!#
!##############################################################################

module minpack_module
    implicit none
    
    ! 模块级变量用于外部函数接口
    integer :: minpack_n
    integer :: minpack_m
    
contains

    !======================================================================
    ! @子程序: lmdif1
    ! @描述: Levenberg-Marquardt方法求解非线性最小二乘问题
    !        这是MINPACK的主要接口之一
    !        
    ! @输入参数:
    !   fcn - 用户提供的误差计算函数
    !   m - 数据点数量
    !   n - 参数数量
    !   x - 初始参数值（输出为优化后的值）
    !   fvec - 误差数组
    !   tol - 收敛容差
    !   maxfev - 最大函数调用次数
    !   info - 输出状态 (0=失败, 1=成功)
    !======================================================================
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
        
        ! 设置默认参数
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
        
        ! 调用底层lmder或lmdir
        call lmdif(fcn, m, n, x, fvec, ftol, xtol, gtol, maxfev_internal, &
                   mode, factor, nprint, info_internal, nfev, wa, lwa)
        
        info = info_internal
        
        deallocate(wa)
        
    end subroutine
    
    !======================================================================
    ! @子程序: lmdif
    ! @描述: Levenberg-Marquardt方法的核心实现
    !======================================================================
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
    
    !======================================================================
    ! @子程序: fdjac2
    ! @描述: 计算雅可比矩阵的近似值（使用有限差分）
    !======================================================================
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
    
    !======================================================================
    ! @子程序: dogleg
    ! @描述: 狗腿法：计算高斯-牛顿方向和梯度方向的凸组合
    !======================================================================
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
    
    !======================================================================
    ! @函数: enorm
    ! @描述: 计算向量的欧几里得范数
    !======================================================================
    function enorm(n, x) result(res)
        integer, intent(in) :: n
        real*8, intent(in) :: x(n)
        real*8 :: res
        
        res = sqrt(sum(x(1:n)**2))
        
    end function
    
    !======================================================================
    ! @子程序: qrfac
    ! @描述: QR分解（使用Householder变换）
    !======================================================================
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
    
    !======================================================================
    ! @函数: enorm2
    ! @描述: 鲁棒欧几里得范数计算（避免溢出和下溢）
    !======================================================================
    function enorm2(n, x) result(res)
        integer, intent(in) :: n
        real*8, intent(in) :: x(n)
        real*8 :: res
        
        real*8 :: rdwarf, rgiant, s1, s2, s3, xabs, x1max, x3max
        integer :: i
        
        rdwarf = sqrt(tiny(rdwarf))
        rgiant = sqrt(huge(rgiant))
        
        s1 = 0.0d0
        s2 = 0.0d0
        s3 = 0.0d0
        x1max = 0.0d0
        x3max = 0.0d0
        
        do i = 1, n
            xabs = abs(x(i))
            
            if (xabs <= rdwarf) then
                if (x3max < xabs) then
                    s3 = 1.0d0 + s3 * (x3max / xabs)**2
                    x3max = xabs
                else if (xabs /= 0.0d0) then
                    s3 = s3 + (xabs / x3max)**2
                end if
            else if (xabs <= rgiant / real(n, 8)) then
                if (x1max < xabs) then
                    s1 = 1.0d0 + s1 * (x1max / xabs)**2
                    x1max = xabs
                else
                    s1 = s1 + (xabs / x1max)**2
                end if
            else
                s2 = s2 + xabs**2
            end if
        end do
        
        if (s1 /= 0.0d0) then
            res = x1max * sqrt(s1 + (s2 / x1max) / x1max)
        else if (s2 /= 0.0d0) then
            if (x3max <= s2) then
                res = sqrt(s2 * (1.0d0 + (x3max / s2) * (x3max * s3)))
            else
                res = sqrt(x3max * ((s2 / x3max) + (x3max * s3)))
            end if
        else
            res = x3max * sqrt(s3)
        end if
        
    end function

end module minpack_module
