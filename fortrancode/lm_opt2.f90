module fitting_module
    integer,parameter :: maxdata=1000
    real*8 x(maxdata),value(maxdata),value1(maxdata)
    real*8 e2,e3,e4,wavelength,x1,sym_e,sym_cal
    real*8 Miller_trans(maxdata,3)
    integer :: family_member_count(maxdata)
    integer :: family_supported(maxdata)
    integer :: family_key(maxdata,3)
    integer :: family_members(maxdata,4,3)
    real*8 :: family_residual_raw(maxdata)
    real*8 :: sym_tq, sym_ta  ! 族二次筛选的绝对容差: q容差, 角度容差
    integer sym_stat
    integer level
    real*8 contribution(maxdata)
    integer tilt_check
    integer :: crystal_system
    integer :: fixhklfile!是否存在固定文件
    integer,allocatable :: fixhkl(:,:)
    integer :: ortho_ab_star ! a*与b*垂直约束标志
    
    ! Miller指数限制相关全局变量（移至模块级）
    integer :: max_h1_in, max_k1_in, max_l1_in  ! 用户输入的Miller指数限制
    integer :: max_h1, max_k1, max_l1  ! 实际使用的Miller指数限制（全局变量）
    integer :: h_user_set, k_user_set, l_user_set  ! 用户设置标志
    real*8 :: max_q  ! 最大q值
    integer :: max_h1_by_cell, max_k1_by_cell, max_l1_by_cell  ! 基于晶胞参数的Miller指数（整数）
    integer :: max_h1_by_q, max_k1_by_q, max_l1_by_q  ! 基于q值的Miller指数（整数）
    real*8 :: max_values(6),min_values(6)
end module


!VERSION 1.0
! 最终基础版本内容
!VERSION 1.1 
! 网页版正式上线
!VERSION 1.2 -2025.6.12
! 受制于超长样品存在严重的tilt影响问题，特别开发tilt模块，作为全新变量重新影响整个计算
!VERSION 1.21 - 2025.6.20
! tilt梯度存在问题，tilt的优化十分不优秀，内部存在一个bug已经修正。确定固定一些晶胞参数，方便后续再优化！
!VERSION 1.3 - 2025.7.22
! 增加固定晶面功能。
!VERSION 1.4 beta -2025.10.13
! 增加理想a*与b*垂直优化-该模式下a*将与b*垂直。
!VERSION 1.5 -2026.1.2
! 重新修改程序，使其合理化，增添更多设置，弥补晶胞参数限制
! VERSION 1.51-2026.1.29
! 多核并行化，该代码以服务器为主
! VERSION 1.7 外部优化

module error_module
    use fitting_module
    implicit none
contains
    !=========================================================================
    ! Symmetry-family scoring contract for upcoming joint matching (Task 1)
    ! ----------------------------------------------------------------------
    ! Canonical family key (v1 only): family_key = (abs(h), abs(k), l).
    ! This matches the existing hk-rule buckets in PRE/backend/services/peak_merge.py.
    !
    ! Supported family cardinalities (v1 only):
    !   - 2-member family: same abs(h), same abs(k), same l, and exactly two
    !     unique sign variants that form an opposite-sign pair on h and/or k.
    !   - 4-member family: same abs(h), same abs(k), same l, and the full set
    !     of sign variants implied by the non-zero h/k magnitudes.
    !   - Unsupported shapes MUST be rejected explicitly by later family logic:
    !     examples include 3-member buckets, duplicate-sign-only buckets, or any
    !     mismatched-sign bucket that does not satisfy the current 2/4-member rule.
    !
    ! Shared observed peak semantics for symmetry-enabled runs:
    !   - One observed diffraction peak may be shared by every member inside a
    !     supported family.
    !   - Each family member computes its own member_to_observed_error against the
    !     same observed peak (same observed q/psi source, different theoretical q/psi).
    !   - If no supported family exists for a theoretical reflection, that reflection
    !     remains an ungrouped singleton and uses the legacy single-HKL residual.
    !
    ! Family residual contract that will replace raw per-member summation:
    !   family_residual = mean(member_to_observed_error) + lambda * intra_family_spread
    ! where
    !   member_to_observed_error = abs(q_theory - q_obs) * e3
    !                            + abs(psi_theory - psi_obs) * e2
    !                            + V / e4
    !   intra_family_spread = max pairwise theoretical delta within the family,
    !   measured in (q, psi) space for the current parameter set.
    ! The spread term is evaluated only once per family. After taking the family
    ! mean, later code MUST NOT re-sum the member residuals again.
    !
    ! Normalized totalSq/error_total aggregation contract:
    !   totalSq = sum(unit_residual)
    ! over active scoring units, where each unit is either one supported family
    ! or one ungrouped singleton. Therefore a 2-member or 4-member family adds
    ! exactly one normalized residual to totalSq/error_total, not one term per member.
    !=========================================================================
    subroutine reset_family_state(diffraction_num)
        integer, intent(in) :: diffraction_num

        family_member_count(1:diffraction_num) = 1
        family_supported(1:diffraction_num) = 0
        family_key(1:diffraction_num, 1:3) = 0
        family_members(1:diffraction_num, 1:4, 1:3) = 0
        family_residual_raw(1:diffraction_num) = 0.0d0
    end subroutine

    subroutine determine_symmetry_merge_mode(alpha_deg, beta_deg, gamma_deg, merge_mode)
        real*8, intent(in) :: alpha_deg, beta_deg, gamma_deg
        integer, intent(out) :: merge_mode
        real*8, parameter :: esys_tol_deg = 3.0d0
        logical :: alpha_near_90, beta_near_90, gamma_near_90

        alpha_near_90 = abs(alpha_deg - 90.0d0) <= esys_tol_deg
        beta_near_90 = abs(beta_deg - 90.0d0) <= esys_tol_deg
        gamma_near_90 = abs(gamma_deg - 90.0d0) <= esys_tol_deg

        merge_mode = 0
        if (alpha_near_90 .and. beta_near_90 .and. gamma_near_90) then
            merge_mode = 1
        else if ((.not. alpha_near_90) .and. beta_near_90 .and. gamma_near_90) then
            merge_mode = 2
        else if (alpha_near_90 .and. (.not. beta_near_90) .and. gamma_near_90) then
            merge_mode = 3
        else if (alpha_near_90 .and. beta_near_90 .and. (.not. gamma_near_90)) then
            merge_mode = 4
        end if
    end subroutine

    logical function family_matches_merge_mode(member_count, members, merge_mode)
        integer, intent(in) :: member_count, merge_mode
        integer, intent(in) :: members(4,3)

        integer :: h1, h2, k1, k2, l1, l2

        family_matches_merge_mode = .false.
        if (merge_mode == 0) return
        if (member_count == 1) then
            family_matches_merge_mode = .true.
            return
        end if

        if (merge_mode == 1) then
            if (member_count == 2 .or. member_count == 4) family_matches_merge_mode = .true.
            return
        end if

        if (member_count /= 2) return

        h1 = members(1,1)
        k1 = members(1,2)
        l1 = members(1,3)
        h2 = members(2,1)
        k2 = members(2,2)
        l2 = members(2,3)

        select case (merge_mode)
        case (2)
            family_matches_merge_mode = (h1 == -h2 .and. k1 == k2 .and. l1 == l2)
        case (3)
            family_matches_merge_mode = (h1 == h2 .and. k1 == -k2 .and. l1 == l2)
        case (4)
            family_matches_merge_mode = (h1 == h2 .and. k1 == k2 .and. l1 == -l2)
        end select
    end function

    subroutine build_family_bucket(abs_h, abs_k, l_value, merge_mode, member_count, supported, members)
        integer, intent(in) :: abs_h, abs_k, l_value, merge_mode
        integer, intent(out) :: member_count, supported
        integer, intent(out) :: members(4,3)

        members(:, :) = 0
        member_count = 1
        supported = 0

        if (merge_mode == 0) then
            members(1, :) = (/ abs_h, abs_k, l_value /)
            return
        end if

        if (merge_mode == 1) then
            if (abs_h == 0 .and. abs_k == 0) then
                if (l_value /= 0) then
                    member_count = 2
                    supported = 1
                    members(1, :) = (/ 0, 0, l_value /)
                    members(2, :) = (/ 0, 0, -l_value /)
                else
                    members(1, 1) = 0
                    members(1, 2) = 0
                    members(1, 3) = 0
                end if
            else if (abs_h > 0 .and. abs_k > 0) then
                member_count = 4
                supported = 1
                members(1, :) = (/ abs_h,  abs_k, l_value /)
                members(2, :) = (/ abs_h, -abs_k, l_value /)
                members(3, :) = (/ -abs_h, abs_k, l_value /)
                members(4, :) = (/ -abs_h, -abs_k, l_value /)
            else if (abs_h > 0) then
                member_count = 2
                supported = 1
                members(1, :) = (/ abs_h, 0, l_value /)
                members(2, :) = (/ -abs_h, 0, l_value /)
            else
                member_count = 2
                supported = 1
                members(1, :) = (/ 0, abs_k, l_value /)
                members(2, :) = (/ 0, -abs_k, l_value /)
            end if
            return
        end if

        if (merge_mode == 2 .and. abs_h > 0) then
            member_count = 2
            supported = 1
            members(1, :) = (/ abs_h, abs_k, l_value /)
            members(2, :) = (/ -abs_h, abs_k, l_value /)
        else if (merge_mode == 3 .and. abs_k > 0) then
            member_count = 2
            supported = 1
            members(1, :) = (/ abs_h, abs_k, l_value /)
            members(2, :) = (/ abs_h, -abs_k, l_value /)
        else if (merge_mode == 4 .and. l_value /= 0) then
            member_count = 2
            supported = 1
            members(1, :) = (/ abs_h, abs_k, l_value /)
            members(2, :) = (/ abs_h, abs_k, -l_value /)
        else
            members(1, :) = (/ abs_h, abs_k, l_value /)
        end if
    end subroutine

    subroutine compute_reflection_coordinates(h_value, k_value, l_value, c_axis, tilt_angle, V, &
                                              A11, B11, C11, D11, E11, F11, q_value, coord_value, valid)
        integer, intent(in) :: h_value, k_value, l_value
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: q_value, coord_value
        logical, intent(out) :: valid

        real*8, parameter :: pi = 3.14159265358979323846d0
        real*8 :: d, theta, d1, y1, phi_value, phi_asin

        valid = .false.
        q_value = 1.0d10
        coord_value = 1.0d10

        if (l_value == 0) then
            y1 = 0.0d0
        else
            y1 = dble(l_value) / c_axis
        end if

        d = 1.0d0 / sqrt((A11 * h_value**2 + B11 * k_value**2 + C11 * l_value**2 + &
                         2.0d0 * D11 * h_value * k_value + 2.0d0 * E11 * k_value * l_value + &
                         2.0d0 * F11 * h_value * l_value) / V**2)

        theta = asin(wavelength / (2.0d0 * d))
        if (theta /= theta) return

        q_value = 2.0d0 * pi / d
        d1 = 1.0d0 / wavelength * sin(2.0d0 * theta)

        if (tilt_check == 1) then
            phi_asin = (y1 / cos(tilt_angle) + 1.0d0 / d * sin(theta) * tan(tilt_angle)) / d1
            if (phi_asin > 1.0d0 .or. phi_asin < -1.0d0) then
                phi_value = pi / 2.0d0
            else
                phi_value = asin(phi_asin)
            end if
        else
            if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
                phi_value = pi / 2.0d0
            else
                phi_value = asin(y1 / d1)
            end if
        end if

        if (level == 1) then
            coord_value = phi_value * 180.0d0 / pi
        else
            coord_value = y1
        end if

        valid = .true.
    end subroutine

    real*8 function calculate_family_spread(member_count, q_values, coord_values)
        integer, intent(in) :: member_count
        real*8, intent(in) :: q_values(4), coord_values(4)

        integer :: i, j
        real*8 :: spread_local

        calculate_family_spread = 0.0d0
        if (member_count <= 1) return

        do i = 1, member_count - 1
            do j = i + 1, member_count
                spread_local = abs(q_values(i) - q_values(j)) * e3 + &
                               abs(coord_values(i) - coord_values(j)) * e2
                if (spread_local > calculate_family_spread) then
                    calculate_family_spread = spread_local
                end if
            end do
        end do
    end function

    subroutine calculate_family_unit_residual(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                              A11, B11, C11, D11, E11, F11, unit_residual, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4,3)
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: unit_residual
        logical, intent(out) :: valid

        integer :: member_idx
        real*8 :: q_values(4), coord_values(4), member_error_sum
        logical :: member_valid

        unit_residual = 1.0d10
        q_values(:) = 0.0d0
        coord_values(:) = 0.0d0
        member_error_sum = 0.0d0
        valid = .true.

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_values(member_idx), &
                                                coord_values(member_idx), member_valid)
            if (.not. member_valid) then
                valid = .false.
                return
            end if

            member_error_sum = member_error_sum + abs(q_values(member_idx) - value1(observed_idx)) * e3 + &
                               abs(coord_values(member_idx) - value(observed_idx)) * e2 + V / e4
        end do

        unit_residual = member_error_sum / dble(member_count)
    end subroutine

    subroutine evaluate_family_candidate(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                         A11, B11, C11, D11, E11, F11, selected_count, selected_supported, &
                                         selected_members, unit_residual, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4,3)
        integer, intent(out) :: selected_count, selected_supported
        integer, intent(out) :: selected_members(4,3)
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: unit_residual
        logical, intent(out) :: valid

        integer :: member_idx, pass_count, best_member_idx
        real*8 :: q_value, coord_value, residual, pass_sum, best_residual
        logical :: member_valid

        selected_members(:, :) = 0
        selected_count = 0
        selected_supported = 0
        unit_residual = 1.0d10
        valid = .false.
        pass_count = 0
        pass_sum = 0.0d0
        best_member_idx = 0
        best_residual = 1.0d10

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_value, coord_value, member_valid)
            if (.not. member_valid) cycle

            residual = abs(q_value - value1(observed_idx)) * e3 + abs(coord_value - value(observed_idx)) * e2 + V / e4
            if (residual < best_residual) then
                best_residual = residual
                best_member_idx = member_idx
            end if

            if (abs(q_value - value1(observed_idx)) <= sym_tq .and. &
                abs(coord_value - value(observed_idx)) <= sym_ta) then
                pass_count = pass_count + 1
                selected_members(pass_count, :) = members(member_idx, :)
                pass_sum = pass_sum + residual
            end if
        end do

        if (pass_count >= 2) then
            selected_count = pass_count
            selected_supported = 1
            unit_residual = pass_sum / dble(pass_count)
            valid = .true.
        else if (pass_count == 1) then
            selected_count = 1
            selected_supported = 0
            unit_residual = pass_sum
            valid = .true.
        else if (best_member_idx > 0) then
            selected_count = 1
            selected_supported = 0
            selected_members(1, :) = members(best_member_idx, :)
            unit_residual = best_residual
            valid = .true.
        end if
    end subroutine

    subroutine pick_best_singleton_from_family(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                               A11, B11, C11, D11, E11, F11, best_h, best_k, best_l, &
                                               best_residual, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4,3)
        integer, intent(out) :: best_h, best_k, best_l
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: best_residual
        logical, intent(out) :: valid

        integer :: member_idx
        real*8 :: q_value, coord_value, residual
        logical :: member_valid

        best_h = 0
        best_k = 0
        best_l = 0
        best_residual = 1.0d10
        valid = .false.

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_value, coord_value, member_valid)
            if (.not. member_valid) cycle

            residual = abs(q_value - value1(observed_idx)) * e3 + abs(coord_value - value(observed_idx)) * e2 + V / e4
            if (residual < best_residual) then
                best_residual = residual
                best_h = members(member_idx, 1)
                best_k = members(member_idx, 2)
                best_l = members(member_idx, 3)
                valid = .true.
            end if
        end do
    end subroutine

    subroutine set_family_assignment(observed_idx, representative_h, representative_k, representative_l, &
                                     member_count, supported, members, unit_residual)
        integer, intent(in) :: observed_idx, representative_h, representative_k, representative_l
        integer, intent(in) :: member_count, supported
        integer, intent(in) :: members(4,3)
        real*8, intent(in) :: unit_residual

        Miller_trans(observed_idx, 1) = representative_h
        Miller_trans(observed_idx, 2) = representative_k
        Miller_trans(observed_idx, 3) = representative_l
        family_member_count(observed_idx) = member_count
        family_supported(observed_idx) = supported
        family_key(observed_idx, 1) = abs(representative_h)
        family_key(observed_idx, 2) = abs(representative_k)
        family_key(observed_idx, 3) = representative_l
        family_members(observed_idx, :, :) = members(:, :)
        family_residual_raw(observed_idx) = unit_residual
    end subroutine

    !=== The routine calculates fitting error === 误差计算，绝对值差
    subroutine calcfiterr(diffraction_num,nparm,parm,fiterr,iflag)
        use fitting_module, only: value, value1, e2, e3, e4, sym_e, sym_cal, contribution, &
                                  family_supported, family_member_count, family_members, &
                                  tilt_check, ortho_ab_star, crystal_system, max_values, min_values, sym_stat
        !必须要参数----》观测点数量，参数数量，参数【数组】，最终误差结果，信息
        !将会调用calcfitval

        integer diffraction_num,nparm,iflag,i
        real*8 :: parm(nparm),fiterr(diffraction_num),fitval(diffraction_num),fitval1(diffraction_num)
        real*8 :: V
        real*8 :: a, b, c, alpha, beta, gamma
        real*8 :: A11, B11, C11, D11, E11, F11
        real*8 :: tilt_angle
        logical :: unit_valid


        ! 调用函数 ！
        call calcfitval(diffraction_num,nparm,parm,fitval,fitval1,V)!计算y轴数值，用以计算误差

        !误差核心计算,fitval为q,fitval1为phi
        sym_cal=0

        if (sym_stat==1) then
            a = parm(1)
            b = parm(2)
            c = parm(3)

            if (ortho_ab_star == 1) then
                alpha = parm(4) * 3.14159265358979323846d0 / 180.0d0
                beta = parm(5) * 3.14159265358979323846d0 / 180.0d0
                gamma = acos(cos(alpha) * cos(beta))
                parm(6) = gamma * 180.0d0 / 3.14159265358979323846d0
            else if (crystal_system == 1) then
                alpha = 3.14159265358979323846d0 / 2.0d0
                beta = 3.14159265358979323846d0 / 2.0d0
                gamma = 3.14159265358979323846d0 / 2.0d0
            else
                alpha = parm(4) * 3.14159265358979323846d0 / 180.0d0
                beta = parm(5) * 3.14159265358979323846d0 / 180.0d0
                gamma = parm(6) * 3.14159265358979323846d0 / 180.0d0
            end if

            tilt_angle = 0.0d0
            if (tilt_check == 1) then
                tilt_angle = parm(7) * 3.14159265358979323846d0 / 180.0d0
            end if

            A11 = b**2 * c**2 * sin(alpha)**2
            B11 = a**2 * c**2 * sin(beta)**2
            C11 = a**2 * b**2 * sin(gamma)**2
            D11 = a * b * c**2 * (cos(alpha) * cos(beta) - cos(gamma))
            E11 = a**2 * b * c * (cos(beta) * cos(gamma) - cos(alpha))
            F11 = a * b**2 * c * (cos(gamma) * cos(alpha) - cos(beta))

            do i = 1, diffraction_num
                if (family_supported(i) == 1) then
                    call calculate_family_unit_residual(i, family_member_count(i), family_members(i, :, :), &
                                                        c, tilt_angle, V, A11, B11, C11, D11, E11, F11, &
                                                        fiterr(i), unit_valid)
                    if (.not. unit_valid) then
                        fiterr(i) = 100000.0d0
                    end if
                else
                    fiterr(i) = abs(fitval(i) - value1(i)) * e3 + abs(fitval1(i) - value(i)) * e2 + V / e4
                end if
            end do

        else
            do i = 1, diffraction_num
                fiterr(i) = abs(fitval(i) - value1(i)) * e3 + abs(fitval1(i) - value(i)) * e2 + V / e4
            end do
        end if

        ! sym_cal 晶体对称性奖励 (始终生效)
        do i=4,6

            if (abs(parm(i)-90)<2.0d0) then
                sym_cal=sym_cal+1
            end if

        end do

        if (sym_cal==3) then
            fiterr(:)=fiterr(:)*sym_e*contribution(1:diffraction_num)
        else if (sym_cal==2) then
            fiterr(:)=fiterr(:)*(0.5d0+sym_e/2.0d0)*contribution(1:diffraction_num)
        else
            fiterr(:)=fiterr(:)*contribution(1:diffraction_num)
        end if


        if (sym_cal<=1) then
            if (any(parm(1:6) > max_values)) then
                fiterr(:) = fiterr(:) * 5.0
            end if
            
            if (any(parm(1:6) < min_values)) then
                fiterr(:) = fiterr(:) * 5.0
            end if
        end if

    end subroutine

    subroutine error_cal_initial(diffraction_num, parm)
        use fitting_module, only: Miller_trans, tilt_check, ortho_ab_star, crystal_system, &
                                  max_h1, max_k1, max_l1, value, value1, e2, e3, e4, sym_stat, &
                                  family_supported, family_member_count, family_members, sym_tq, &
                                  fixhkl, fixhklfile
        !修改说明：
        !1. Miller指数限制已移至主程序计算，使用全局变量max_h1, max_k1, max_l1
        !2. 重构算法：边计算边比较边记录，避免存储无用数据，大幅降低内存占用
        !3. 优化逻辑：每个实验衍射点独立寻找最佳匹配晶面，无需预存所有计算结果

        integer, intent(in) :: diffraction_num
        real(kind=8), intent(inout) :: parm(:)

        !内部变量
        integer :: a1, b1, c1  !当前遍历的Miller指数
        integer :: k, n, merge_mode     !循环变量
        integer :: num_ref     !最佳匹配位置记录
        integer :: valid_count !有效计算点计数器
        integer :: current_member_count, current_supported
        integer :: current_members(4,3), candidate_member_count, candidate_supported
        integer :: candidate_members(4,3)

        real(kind=8) :: a, b, c, alpha, beta, gamma
        real(kind=8) :: V
        real(kind=8) :: A11, B11, C11, D11, E11, F11
        real(kind=8) :: theta, d, q, PHI, d1, y1
        real(kind=8), parameter :: pi = 3.14159265358979323846d0
        real(kind=8) :: tilt_angle, PHI_asin
        real(kind=8) :: error_lowest, error_mid, unit_residual
        logical :: unit_valid

        !中间计算变量（无需大数组存储）
        real(kind=8) :: current_q, current_PHI_or_y1, current_theta
        integer :: current_h, current_k, current_l
        real(kind=8) :: current_V
        real(kind=8), allocatable :: min_error_list(:)

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
        if (ortho_ab_star == 1) then
            alpha = parm(4) * pi / 180
            beta = parm(5) * pi / 180
            gamma = acos(cos(alpha) * cos(beta))
            parm(6) = gamma * 180 / pi
        else if (crystal_system == 1) then
            alpha = pi / 2
            beta = pi / 2
            gamma = pi / 2
        else
            alpha = parm(4) * pi / 180
            beta = parm(5) * pi / 180
            gamma = parm(6) * pi / 180
        end if

        call determine_symmetry_merge_mode(alpha * 180.0d0 / pi, beta * 180.0d0 / pi, gamma * 180.0d0 / pi, merge_mode)

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
        call reset_family_state(diffraction_num)

        current_V = V ! 记录当前体积

        ! 2. 外层循环：遍历理论晶面 (h, k, l)
        ! 将计算量大的部分放在外层，确保每组 hkl 只计算一次物理量
        !$OMP PARALLEL DO COLLAPSE(3) DEFAULT(SHARED) &
        !$OMP PRIVATE(c1, b1, a1, y1, d, theta, q, d1, PHI_asin, PHI, k, error_mid, &
        !$OMP         current_member_count, current_supported, current_members, candidate_member_count, &
        !$OMP         candidate_supported, candidate_members, unit_residual, unit_valid) &
        !$OMP SCHEDULE(DYNAMIC)
        do c1 = 0, max_l1
            do b1 = -max_k1, max_k1
                do a1 = -max_h1, max_h1

                    if (sym_stat == 1) then
                        if (merge_mode == 1) then
                            if (a1 < 0) cycle
                            if (a1 == 0 .and. b1 < 0) cycle
                        else if (merge_mode == 2) then
                            if (a1 < 0) cycle
                        else if (merge_mode == 3) then
                            if (b1 < 0) cycle
                        end if
                    end if
                    
                    ! 1. 计算 y1 (注意：y1 虽然依赖 c1，但放在 PRIVATE 里最安全)
                    if (c1 == 0) then
                        y1 = 0.0d0
                    else
                        y1 = real(c1) / c
                    end if

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
                    
                    ! PHI 的计算 (保持原样，它们现在都是私有的)
                    if (tilt_check == 1) then
                        PHI_asin = (y1 / cos(tilt_angle) + 1.0d0 / d * sin(theta) * tan(tilt_angle)) / d1
                        if (PHI_asin > 1.0d0 .or. PHI_asin < -1.0d0) then
                            PHI = pi / 2.0d0
                        else
                            PHI = asin(PHI_asin)
                        end if
                    else
                        if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
                            PHI = pi / 2.0d0
                        else
                            PHI = asin(y1 / d1)
                        end if
                    end if
                    
                    !================::DEBUG::=====================
                    ! if (a1 == 1 .and. b1 == 1 .and. c1 == 0) then
                    !     print*,a1,b1,c1
                    !     print*,"q",q
                    !     print*,"d",d
                    !     print*,"wavelength",wavelength
                    !     print*,a,b,c,alpha*180/pi,beta*180/pi,gamma*180/pi
                    !     stop
                    ! end if
                    

                    !===========================================
                    ! 2. 比较与更新记录
                    if (sym_stat == 1 .and. merge_mode /= 0) then
                        call build_family_bucket(abs(a1), abs(b1), c1, merge_mode, &
                                                 candidate_member_count, candidate_supported, candidate_members)
                        do k = 1, diffraction_num
                            call evaluate_family_candidate(k, candidate_member_count, candidate_members, c, tilt_angle, V, &
                                                           A11, B11, C11, D11, E11, F11, current_member_count, &
                                                           current_supported, current_members, unit_residual, unit_valid)
                            if (.not. unit_valid) cycle

                            if (unit_residual < min_error_list(k)) then
                                !$OMP CRITICAL(update_min)
                                if (unit_residual < min_error_list(k)) then
                                    min_error_list(k) = unit_residual
                                    call set_family_assignment(k, a1, b1, c1, current_member_count, current_supported, &
                                                               current_members, unit_residual)
                                end if
                                !$OMP END CRITICAL(update_min)
                            end if
                        end do
                    else
                        do k = 1, diffraction_num
                            if (level == 1) then
                                error_mid = abs(q - value1(k)) * e3 + abs(PHI * 180.0d0 / pi - value(k)) * e2
                            else if (level == 2) then
                                error_mid = abs(q - value1(k)) * e3 + abs(y1 - value(k)) * e2
                            end if

                            ! --- 全局比较保护区 ---
                            ! 只有当发现更小值时，才进入受保护状态
                            if (error_mid < min_error_list(k)) then
                                !$OMP CRITICAL(update_min)
                                if (error_mid < min_error_list(k)) then
                                    min_error_list(k) = error_mid
                                    Miller_trans(k, 1) = a1
                                    Miller_trans(k, 2) = b1
                                    Miller_trans(k, 3) = c1
                                    current_members(:, :) = 0
                                    current_members(1, :) = (/ a1, b1, c1 /)
                                    call set_family_assignment(k, a1, b1, c1, 1, 0, current_members, error_mid)
                                end if
                                !$OMP END CRITICAL(update_min)
                            end if
                        end do
                    end if

                end do 
            end do
        end do
        !$OMP END PARALLEL DO

        ! 3. 固定晶面处理 (在释放min_error_list之前执行)
        if (allocated(fixhkl)) then
            do k = 1, fixhklfile
                Miller_trans(fixhkl(k, 1), 1:3) = fixhkl(k, 2:4)
                current_members(:, :) = 0
                current_members(1, :) = fixhkl(k, 2:4)
                call set_family_assignment(fixhkl(k, 1), fixhkl(k, 2), fixhkl(k, 3), fixhkl(k, 4), &
                                           1, 0, current_members, min_error_list(fixhkl(k, 1)))
            end do
        end if

        ! 释放临时数组
        if (allocated(min_error_list)) deallocate(min_error_list)

        return

    end subroutine error_cal_initial

    subroutine calcfitval(diffraction_num, nparm, parm, fitval, fitval1, V)
        implicit real*8 (a-h, o-z)
        integer diffraction_num, nparm
        real*8 :: parm(nparm), fitval(diffraction_num), fitval1(diffraction_num)
        real*8 :: a, b, c, alpha, beta, gamma
        real*8 :: A11, B11, C11, D11, E11, F11, V
        real*8 :: h1, k1, l1
        real*8 :: q, PHI, d, d1, y1
        real*8, parameter :: pi = 3.14159265358979323846d0
        real(kind=8) :: tilt_angle, PHI_asin, theta
        integer :: i

        a = parm(1)
        b = parm(2)
        c = parm(3)

        if (ortho_ab_star == 1) then
            alpha = parm(4) * pi / 180
            beta = parm(5) * pi / 180
            gamma = acos(cos(alpha) * cos(beta))
            parm(6) = gamma * 180 / pi
        else if (crystal_system == 1) then
            alpha = pi / 2
            beta = pi / 2
            gamma = pi / 2
        else
            alpha = parm(4) * pi / 180
            beta = parm(5) * pi / 180
            gamma = parm(6) * pi / 180
        end if

        tilt_angle = 0.0d0
        if (tilt_check == 1) then
            tilt_angle = parm(7) * pi / 180
        end if

        V = a * b * c * (1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + 2 * cos(alpha) * cos(beta) * cos(gamma))**0.5

        if (isnan(V) .or. V < 0.01) then
            V = 10000000
        end if
        PHI = 0

        A11 = b**2 * c**2 * sin(alpha)**2
        B11 = a**2 * c**2 * sin(beta)**2
        C11 = a**2 * b**2 * sin(gamma)**2
        D11 = a * b * c**2 * (cos(alpha) * cos(beta) - cos(gamma))
        E11 = a**2 * b * c * (cos(beta) * cos(gamma) - cos(alpha))
        F11 = a * b**2 * c * (cos(gamma) * cos(alpha) - cos(beta))

        do i = 1, diffraction_num
            h1 = Miller_trans(i, 1)
            k1 = Miller_trans(i, 2)
            l1 = Miller_trans(i, 3)

            if (l1 == 0) then
                y1 = 0
            else
                y1 = real(l1) / c
            end if

            d = 1 / sqrt((A11 * h1**2 + B11 * k1**2 + C11 * l1**2 + 2 * D11 * h1 * k1 &
                       & + 2 * E11 * k1 * l1 + 2 * F11 * h1 * l1) / V**2)

            theta = asin(wavelength / (2 * d))

            q = 2 * pi / d

            d1 = sqrt(4 * d**2 - wavelength**2) / (2 * d**2)

            if (tilt_check == 1) then
                PHI_asin = (y1 / cos(tilt_angle) + 1 / d * sin(theta) * tan(tilt_angle)) / d1
                if (PHI_asin > 1.0d0 .or. PHI_asin < -1.0d0) then
                    PHI = pi / 2
                else
                    PHI = asin(PHI_asin)
                end if
            else
                if (y1 / d1 > 1 .or. y1 / d1 < -1) then
                    PHI = pi / 2
                else
                    PHI = asin(y1 / d1)
                end if
            end if

            fitval(i) = q

            if (level == 1) then
                fitval1(i) = PHI * 180 / pi
            else if (level == 2) then
                fitval1(i) = y1
            end if

        end do

    end subroutine

    !==========================================================================
    !==========================================================================
    !**************************************************************************


end module




program LMfit
    use fitting_module
    use error_module
    implicit real*8 (a-h,o-z)
    integer :: nparm
    integer :: diffraction_num,num_cell
    integer :: maxcall,info,ierror
    real*8,allocatable :: parm(:) !a,b,c,alpha,beta,gamma
    real*8 fiterr(maxdata),fitval(maxdata),fitval1(maxdata)
    character(len=512) :: filename_input,filename_cell,filename_dif,input_type,input_type2,input_type3
    character(len=512) :: filename1,filename2,filename3,filename_5!定义文件名
    real*8,allocatable :: cell_parameter(:,:),error_total(:)
    character c80tmp*80
    real*8 :: amin,amax,bmin,bmax,cmin,cmax,alphamin,alphamax,betamin,betamax,gammamin,gammamax
    character(len=256) :: buffer  ! 用于暂存读取的一行文本
    integer :: io_status          ! 用于捕获读取状态
    ! external calcfiterr
    
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
    end if

    !----------------------------------------命令行输入结束---------------------------------------
    !---------------------------------------------------INPUT文件读取部分-----------------------------------------------    
    !读取cell_n.txt文件中的数据
    open(unit=1,file=filename_input,status='old',action='read')!打开input文件,并且将文件的内容读取到1号文件中
    fixhklfile = 0!初始化
    ortho_ab_star = 0!初始化a*与b*垂直约束标志
    !文件第一行为波长，第二行为检测器距离，第三行为检测器类型
    do i=1,28
        if (i==1) then
            read(1,*) wavelength
        else if (i==4) then
            read(1,*) num_cell!读取晶胞数目
        else if (i==13) then
            read(1,*) level!读取层次,1是q-psi,2是theta模式
        else if (i==14) then
            read(1,*) ortho_ab_star!读取a*与b*垂直约束标志
        else if (i==15) then
            read(1,*) e2
        else if (i==16) then
            read(1,*) e3
        else if (i==17) then
            !打印这一行的所有内容
            read(1,*) e4
        else if (i==18) then
            read(1,*) x1
        else if (i==19) then
            ! read(1,*) max_h1_in, max_k1_in, max_l1_in  !读取用户设定的Miller指数限制
            read(1, '(A)') buffer
            read(buffer, *, iostat=io_status) max_h1_in, max_k1_in, max_l1_in
            ! 3. 检查读取状态
            if (io_status /= 0) then
                ! 如果读取 3 个数失败（io_status不为0），说明输入不足3个
                ! 尝试只读取第 1 个数
                read(buffer, *, iostat=io_status) max_h1_in
                ! 如果读取 1 个数成功，且该数为 0
                if (io_status == 0 .and. max_h1_in == 0) then
                    ! 用户输入了单个 0，触发“默认逻辑”
                    max_h1_in = 0
                    max_k1_in = 0
                    max_l1_in = 0
                else
                    ! 既不是3个数，也不是单个0，说明格式真的错了
                    write(*,*) 'ERROR: Wrong input in line 19'
                    stop
                end if
            end if            


        else if (i==23) then
            read(1,*) sym_stat
        else if (i==24) then
            read(1,*) sym_e
        else if (i==20) then
            read(1,*) sym_tq
            if (sym_tq <= 0.0d0) sym_tq = 0.02d0  ! 默认值
        else if (i==21) then
            read(1,*) sym_ta
            if (sym_ta <= 0.0d0) sym_ta = 1.0d0  ! 默认值
        else if (i == 25) then
            read(1,*) amin,bmin,cmin,alphamin,betamin,gammamin
        else if (i == 26) then
            read(1,*) amax,bmax,cmax,alphamax,betamax,gammamax
        else if (i == 27) then
            read(1,*) tilt_check!确定是否优化tilt-0等默认不优化，1为优化
        else if (i == 28) then
            read(1,*) fixhklfile!确定是否固定hkl，如果/=0，则打开hkl文件，读取fixhkl数量的文件
        else
            read(1,*)
        end if 
    end do
    close(1)!关闭文件

    !检定是否存在正交限制和单斜（后续开发）限制
    if (abs(alphamax-alphamin) < 0.01d0 .and. abs(betamax-betamin) < 0.01d0  .and. abs(gammamax-gammamin) < 0.01d0) then
        !正交晶体
        crystal_system=1
    else
        crystal_system=0!不进行限制
    end if
    

    !赋予max和min
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

    !================================================================
    !=================== Miller指数限制计算 =========================
    ! 规则说明：
    ! 1. 第一准则：三者都不能超过30
    ! 2. 第二准则：根据amax, bmax, cmax和max(q)计算：max_index = amax * q / (2*pi) + 5
    ! 3. 第三准则：按原算法计算：max_index = int(cell_param / wavelength)，限制在5-30之间
    ! 4. 第二与第三准则冲突时，取最大值
    !================================================================
    
    ! 初始化用户输入标志
    h_user_set = 0
    k_user_set = 0
    l_user_set = 0
    
    ! 检查用户输入
    if (max_h1_in > 0) h_user_set = 1
    if (max_k1_in > 0) k_user_set = 1
    if (max_l1_in > 0) l_user_set = 1
    
    !==============================衍射文件=======================
    ! 必须在Miller指数计算之前读取衍射数据以获取max_q
    open(10,file=filename_dif,status="old")!打开文件！
    diffraction_num=0!数据点数目
    max_q = 0.0d0  !初始化最大q值
    do while(.true.)
        read(10,"(a)",iostat=ierror) c80tmp!防错装置
        if (c80tmp==" ".or.ierror/=0) exit
        diffraction_num=diffraction_num+1
        read(c80tmp,*) value1(diffraction_num),value(diffraction_num),contribution(diffraction_num)!value1-q,value-phi,contribution
        ! 计算最大q值
        if (value1(diffraction_num) > max_q) max_q = value1(diffraction_num)
    end do
    close(10)
    
    ! 计算基于晶胞参数的Miller指数（第三准则：原算法）- 使用int转换为整数
    max_h1_by_cell = int(amax / wavelength)
    max_k1_by_cell = int(bmax / wavelength)
    max_l1_by_cell = int(cmax / wavelength)
    
    ! 限制第三准则的计算结果在5-30之间
    max_h1_by_cell = max(3, min(30, max_h1_by_cell))
    max_k1_by_cell = max(3, min(30, max_k1_by_cell))
    max_l1_by_cell = max(3, min(30, max_l1_by_cell))
    
    ! 计算基于q值的Miller指数（第二准则）- 使用int转换为整数
    max_h1_by_q = int(amax * max_q / (2.0d0 * 3.141592653589793d0) + 3.0d0)
    max_k1_by_q = int(bmax * max_q / (2.0d0 * 3.141592653589793d0) + 3.0d0)
    max_l1_by_q = int(cmax * max_q / (2.0d0 * 3.141592653589793d0) + 3.0d0)
    
    ! 限制第二准则的计算结果在5-30之间
    max_h1_by_q = max(5, min(30, max_h1_by_q))
    max_k1_by_q = max(5, min(30, max_k1_by_q))
    max_l1_by_q = max(5, min(30, max_l1_by_q))
    
    ! 根据用户设置情况确定最终Miller指数限制
    if (h_user_set == 1) then
        ! 用户设置了h的限制
        max_h1 = min(30, max_h1_in)  ! 第一准则：不超过30
        if (max_h1 < 1) max_h1 = 5
    else
        ! 用户未设置h，使用第二和第三准则的最大值
        max_h1 = max(max_h1_by_cell, max_h1_by_q)
        max_h1 = min(30, max_h1)  ! 第一准则：不超过30
    end if
    
    if (k_user_set == 1) then
        ! 用户设置了k的限制
        max_k1 = min(30, max_k1_in)  ! 第一准则：不超过30
        if (max_k1 < 1) max_k1 = 5
    else
        ! 用户未设置k，使用第二和第三准则的最大值
        max_k1 = max(max_k1_by_cell, max_k1_by_q)
        max_k1 = min(30, max_k1)  ! 第一准则：不超过30
    end if
    
    if (l_user_set == 1) then
        ! 用户设置了l的限制
        max_l1 = min(30, max_l1_in)  ! 第一准则：不超过30
        if (max_l1 < 1) max_l1 = 5
    else
        ! 用户未设置l，使用第二和第三准则的最大值
        max_l1 = max(max_l1_by_cell, max_l1_by_q)
        max_l1 = min(30, max_l1)  ! 第一准则：不超过30
    end if
    
    ! ! 输出Miller指数限制信息（调试用）
    ! write(*,*) 'Miller指数限制计算完成:'
    ! write(*,*) 'h限制:', max_h1, '(用户设置:', h_user_set, ', 晶胞算法:', max_h1_by_cell, ', q算法:', max_h1_by_q, ')'
    ! write(*,*) 'k限制:', max_k1, '(用户设置:', k_user_set, ', 晶胞算法:', max_k1_by_cell, ', q算法:', max_k1_by_q, ')'
    ! write(*,*) 'l限制:', max_l1, '(用户设置:', l_user_set, ', 晶胞算法:', max_l1_by_cell, ', q算法:', max_l1_by_q, ')'
    !================================================================
    
    ! 检查a*与b*垂直约束与正交系统的兼容性
    if (ortho_ab_star == 1 .and. crystal_system == 1) then
        write(*,*) 'Warning: Both ortho_ab_star and crystal_system constraints are enabled.'
        write(*,*) 'The ortho_ab_star constraint will take precedence.'
    end if
    !==============================================================

    !==============================固定晶面=======================
    if (fixhklfile > 0) then
        allocate(fixhkl(fixhklfile,4))!每个参数：num_diff,h,k,l
        open(11,file="fixhkl.txt",status="old")!打开文件！
        do i = 1, fixhklfile
            ! read(10,"(a)",iostat=ierror) c80tmp!防错装置
            ! if (c80tmp==" ".or.ierror/=0) exit
            read(11,*) fixhkl(i,1),fixhkl(i,2),fixhkl(i,3),fixhkl(i,4)
        end do
        close(11)
    end if
    


    !====================晶胞参数文件=======================
    open(unit=2,file=filename_cell,status='old',action='read')!打开cell_n文件,并且将文件的内容读取到2号文件中
    !读取每一行的数据，然后将其赋值给cell_parameter
    
    nparm = 0 !初始化
    if (tilt_check == 1) then
        ! 有tilt情况：7个参数 (a,b,c,alpha,beta,gamma,tilt_angle)
        allocate(cell_parameter(num_cell,7))
        nparm = 7
    else
        ! 无tilt情况：6个参数 (a,b,c,alpha,beta,gamma)
        allocate(cell_parameter(num_cell,6))
        nparm = 6
    end if

    ! 读取晶胞参数文件（保持原有格式）
    if (tilt_check == 1) then
        do i=1,num_cell
            read(2,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6),cell_parameter(i,7)
        end do
    else
        do i=1,num_cell
            read(2,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6)
        end do
    end if
    close(2)!关闭文件
    !====================================================

    allocate(error_total(num_cell))

    allocate(parm(nparm))
    !读取parm

    do i=1,num_cell
        ! 设置参数数组（保持原有格式）

        if (tilt_check == 1) then
            parm(1)=cell_parameter(i,1)  ! a
            parm(2)=cell_parameter(i,2)  ! b
            parm(3)=cell_parameter(i,3)  ! c
            parm(4)=cell_parameter(i,4)  ! alpha
            parm(5)=cell_parameter(i,5)  ! beta
            parm(6)=cell_parameter(i,6)  ! gamma
            parm(7)=cell_parameter(i,7)  ! tilt_angle
        else
            parm(1)=cell_parameter(i,1)  ! a
            parm(2)=cell_parameter(i,2)  ! b
            parm(3)=cell_parameter(i,3)  ! c
            parm(4)=cell_parameter(i,4)  ! alpha
            parm(5)=cell_parameter(i,5)  ! beta
            parm(6)=cell_parameter(i,6)  ! gamma
        end if

        !寻找miller指数
        !max_h1_in, max_k1_in, max_l1_in：
        !假定q在纵和横
        call error_cal_initial(diffraction_num,parm)

        call lmdif1(calcfiterr,diffraction_num,nparm,parm(:),fiterr(1:diffraction_num),tol,maxcall,info)!cakcfiterr为计算误差程序
        !lmdif提供的是：1.误差数组，2.总观测数据数量，3.拟合参数数量=3+1，4. 拟合参数，5.各个参数的误差，6.收敛限，7最大步数，8.结束信息


        !write(*,*) parm(1),parm(2),parm(3),parm(4),parm(5),parm(6),fiterr(1:diffraction_num)
        !导出error
        ! Symmetry-family aggregation reminder:
        ! `calcfiterr()` now writes one normalized residual per active observed unit.
        ! In symmetry-enabled runs, a supported 2-member / 4-member family is already
        ! collapsed to one family-level `fiterr(j)` before this loop. Unsupported or
        ! non-family cases remain singleton units. Therefore summing `fiterr(j)` here
        ! is the intended unit-level accumulation step, not a raw per-member re-sum.
        error_total(i)=0
        do j=1,diffraction_num

            if (isnan(fiterr(j))) then
                fiterr(j)=100000
            end if
            error_total(i)=error_total(i)+fiterr(j)
        end do
        
        ! 更新优化后的参数到cell_parameter数组（保持原有格式）
        if (tilt_check == 1) then
            cell_parameter(i,1)=parm(1)  ! a
            cell_parameter(i,2)=parm(2)  ! b
            cell_parameter(i,3)=parm(3)  ! c
            cell_parameter(i,4)=parm(4)  ! alpha
            cell_parameter(i,5)=parm(5)  ! beta
            cell_parameter(i,6)=parm(6)  ! gamma (在约束模式下为计算值)
            cell_parameter(i,7)=parm(7)  ! tilt_angle
        else
            cell_parameter(i,1)=parm(1)  ! a
            cell_parameter(i,2)=parm(2)  ! b
            cell_parameter(i,3)=parm(3)  ! c
            cell_parameter(i,4)=parm(4)  ! alpha
            cell_parameter(i,5)=parm(5)  ! beta
            cell_parameter(i,6)=parm(6)  ! gamma (在约束模式下为计算值)
        end if

    end do
    


    !将结果写入到文件中
    open(unit=4,file='diffraction.txt',status='unknown',action='write')!打开diffraction文件,并且将误差值写入到4号文件中
    do i=1,num_cell
        write(4,*) error_total(i)
        !write(*,*) "error=",error_total(i,1)
    end do
    close(4)!关闭文件
    
    !打开原始的cell_n文件，将优化后的晶胞参数写入到cell_n_mont文件中
    filename_5=filename_cell(1:len_trim(filename_cell)-4)//'_annealing.txt'
    ! write(*,*) filename_5
    !write(*,*)  "!!!!!!!!!!",cell_parameter(1,1:6)
    open(unit=5,file=filename_5,status='unknown',action='write')!打开cell_n文件,并且将优化后的晶胞参数写入到5号文件中
    
    ! 写入结果文件（保持原有格式，输出6或7个参数）
    do i=1,num_cell
        if (tilt_check == 1) then
            write(5,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6),cell_parameter(i,7)
        else
            write(5,*) cell_parameter(i,1),cell_parameter(i,2),cell_parameter(i,3)&
            &,cell_parameter(i,4),cell_parameter(i,5),cell_parameter(i,6)
        end if
    end do

    close(5)!关闭文件

    
    ! 输出约束信息
    if (ortho_ab_star == 1) then
        write(*,*) "Optimization completed with a* ? b* constraint enabled."
        write(*,*) "Gamma angle was calculated from alpha and beta using: gamma = arccos(cos(alpha)*cos(beta))"
    else
        write(*,*) "Optimization completed."
    end if
    
    write(*,*) " "
end program
