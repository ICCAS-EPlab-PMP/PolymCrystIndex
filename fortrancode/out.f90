module fitting_module
    integer, parameter :: maxdata = 1000
    real*8 x(maxdata), value(maxdata), value1(maxdata)
    real*8 e2, e3, e4, wavelength, x1, sym_e, sym_cal
    real*8 Miller_trans(maxdata, 7)
    integer :: family_member_count(maxdata)
    integer :: family_supported(maxdata)
    integer :: family_key(maxdata, 3)
    integer :: family_members(maxdata, 4, 3)
    real*8 :: family_residual_raw(maxdata)
    real*8 :: family_spread_raw(maxdata)
    real*8 :: sym_tq, sym_ta  ! 族二次筛选的绝对容差: q容差, 角度容差
    integer sym_stat
    integer level
    integer tilt_check
    integer :: fixhklfile
    integer, allocatable :: fixhkl(:, :)
    integer :: max_h1_in, max_k1_in, max_l1_in
    integer :: max_h1, max_k1, max_l1
    integer :: h_user_set, k_user_set, l_user_set
    real*8 :: max_q
    integer :: max_h1_by_cell, max_k1_by_cell, max_l1_by_cell
    integer :: max_h1_by_q, max_k1_by_q, max_l1_by_q
    real*8 :: max_values(6), min_values(6)
    integer :: deduplicate_enabled  ! 峰独占开关 (0=关, 1=开), input.txt line 30
    real*8 :: dedup_penalty  ! 峰独占惩罚系数 (默认1.0), input.txt line 31
    integer :: dedup_sym_mode  ! dedup对称比较模式 (0=精确, 1=canonical), input.txt line 32
    integer :: dedup_loser(maxdata)  ! 峰独占 loser 标记 (0=非loser, 1=loser)
    real*8 :: miller_original(maxdata, 3)  ! dedup 前原始 Miller 指数
    real*8, allocatable :: min_error_list(:)  ! 模块级误差列表
end module


module calhkl
    use fitting_module
    implicit none
contains
    !=========================================================================
    ! Symmetry-family output contract aligned with lm_opt2.f90 (Task 1)
    ! ----------------------------------------------------------------------
    ! Output generation must stay compatible with future family-aware scoring.
    ! The canonical family key is fixed to (abs(h), abs(k), l) for v1, and only
    ! the existing 2-member / 4-member hk-rule semantics are supported.
    !
    ! Supported family semantics:
    !   - 2-member family: one opposite-sign pair over equal abs(h), abs(k), l.
    !   - 4-member family: full sign-variant set over equal abs(h), abs(k), l.
    !   - Unsupported shapes (3-member buckets, duplicate-only sign buckets,
    !     mismatched-sign buckets) are invalid and must be rejected explicitly.
    !
    ! Shared observed peak semantics for symmetry-enabled runs:
    !   - One observed peak may be referenced by all members of a supported family.
    !   - Output artifacts added in later tasks must report that shared observed
    !     peak once, while still preserving legacy-readable outputMiller.txt rows.
    !   - When no supported family exists, the reflection is emitted as a singleton.
    !
    ! Family residual contract shared with the optimizer:
    !   family_residual = mean(member_to_observed_error) + lambda * intra_family_spread
    !   intra_family_spread = max pairwise theoretical delta in (q, psi)
    !   totalSq/error_total = sum of one normalized residual per active family or
    !                         ungrouped singleton; do not re-sum family members.
    !=========================================================================
    subroutine reset_family_state(diffraction_num)
        integer, intent(in) :: diffraction_num

        family_member_count(1:diffraction_num) = 1
        family_supported(1:diffraction_num) = 0
        family_key(1:diffraction_num, 1:3) = 0
        family_members(1:diffraction_num, 1:4, 1:3) = 0
        family_residual_raw(1:diffraction_num) = 0.0d0
        family_spread_raw(1:diffraction_num) = 0.0d0
    end subroutine reset_family_state

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
    end subroutine determine_symmetry_merge_mode

    logical function family_matches_merge_mode(member_count, members, merge_mode)
        integer, intent(in) :: member_count, merge_mode
        integer, intent(in) :: members(4, 3)
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
    end function family_matches_merge_mode

    subroutine build_family_bucket(abs_h, abs_k, l_value, merge_mode, member_count, supported, members)
        integer, intent(in) :: abs_h, abs_k, l_value, merge_mode
        integer, intent(out) :: member_count, supported
        integer, intent(out) :: members(4, 3)

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
                    members(1, :) = (/ 0, 0, 0 /)
                end if
            else if (abs_h > 0 .and. abs_k > 0) then
                member_count = 4
                supported = 1
                members(1, :) = (/ abs_h, abs_k, l_value /)
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
    end subroutine build_family_bucket

    subroutine compute_reflection_coordinates(h_value, k_value, l_value, c_axis, tilt_angle, V, &
                                              A11, B11, C11, D11, E11, F11, q_value, coord_value, &
                                              psi_display_rad, psi_root_rad, two_theta_deg, valid)
        integer, intent(in) :: h_value, k_value, l_value
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: q_value, coord_value, psi_display_rad, psi_root_rad
        real*8, intent(out) :: two_theta_deg
        logical, intent(out) :: valid

        real*8, parameter :: pi = 3.14159265358979323846d0
        real*8 :: d, theta, d1, y1, phi_value, phi_obs, phi_asin

        valid = .false.
        q_value = 1.0d10
        coord_value = 1.0d10
        psi_display_rad = 0.0d0
        psi_root_rad = 0.0d0
        two_theta_deg = 0.0d0

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
        two_theta_deg = theta * 2.0d0 * 180.0d0 / pi

        if (tilt_check == 1) then
            phi_asin = (y1 / cos(tilt_angle) + 1.0d0 / d * sin(theta) * tan(tilt_angle)) / d1
            if (phi_asin > 1.0d0 .or. phi_asin < -1.0d0) then
                phi_obs = pi / 2.0d0
            else
                phi_obs = asin(phi_asin)
            end if
        else
            phi_obs = 0.0d0
        end if

        if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
            phi_value = pi / 2.0d0
        else
            phi_value = asin(y1 / d1)
        end if

        psi_root_rad = phi_value
        if (tilt_check == 1) then
            psi_display_rad = phi_obs
        else
            psi_display_rad = phi_value
        end if

        if (level == 1) then
            coord_value = psi_display_rad * 180.0d0 / pi
        else
            coord_value = y1
        end if

        valid = .true.
    end subroutine compute_reflection_coordinates

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
    end function calculate_family_spread

    subroutine calculate_family_unit_residual(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                              A11, B11, C11, D11, E11, F11, unit_residual, unit_spread, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4, 3)
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: unit_residual, unit_spread
        logical, intent(out) :: valid

        integer :: member_idx
        real*8 :: q_values(4), coord_values(4), member_error_sum
        real*8 :: psi_display_rad, psi_root_rad, two_theta_deg
        logical :: member_valid

        q_values(:) = 0.0d0
        coord_values(:) = 0.0d0
        member_error_sum = 0.0d0
        unit_spread = 0.0d0
        unit_residual = 1.0d10
        valid = .true.

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_values(member_idx), &
                                                coord_values(member_idx), psi_display_rad, psi_root_rad, &
                                                two_theta_deg, member_valid)
            if (.not. member_valid) then
                valid = .false.
                return
            end if

            member_error_sum = member_error_sum + abs(q_values(member_idx) - value1(observed_idx)) * e3 + &
                               abs(coord_values(member_idx) - value(observed_idx)) * e2 + V / e4
        end do

        unit_spread = 0.0d0
        unit_residual = member_error_sum / dble(member_count)
    end subroutine calculate_family_unit_residual

    subroutine evaluate_family_candidate(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                         A11, B11, C11, D11, E11, F11, selected_count, selected_supported, &
                                         selected_members, best_q, best_psi_display_rad, best_psi_root_rad, &
                                         best_two_theta_deg, unit_residual, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4, 3)
        integer, intent(out) :: selected_count, selected_supported
        integer, intent(out) :: selected_members(4, 3)
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: best_q, best_psi_display_rad, best_psi_root_rad, best_two_theta_deg
        real*8, intent(out) :: unit_residual
        logical, intent(out) :: valid

        integer :: member_idx, pass_count, best_member_idx
        real*8 :: q_value, coord_value, psi_display_rad, psi_root_rad, two_theta_deg
        real*8 :: residual, pass_sum, best_residual
        logical :: member_valid

        selected_members(:, :) = 0
        selected_count = 0
        selected_supported = 0
        best_q = 0.0d0
        best_psi_display_rad = 0.0d0
        best_psi_root_rad = 0.0d0
        best_two_theta_deg = 0.0d0
        unit_residual = 1.0d10
        valid = .false.
        pass_count = 0
        pass_sum = 0.0d0
        best_member_idx = 0
        best_residual = 1.0d10

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_value, coord_value, &
                                                psi_display_rad, psi_root_rad, two_theta_deg, member_valid)
            if (.not. member_valid) cycle

            residual = abs(q_value - value1(observed_idx)) * e3 + abs(coord_value - value(observed_idx)) * e2 + V / e4
            if (residual < best_residual) then
                best_residual = residual
                best_member_idx = member_idx
                best_q = q_value
                best_psi_display_rad = psi_display_rad
                best_psi_root_rad = psi_root_rad
                best_two_theta_deg = two_theta_deg
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
            best_member_idx = 1
            call compute_reflection_coordinates(selected_members(1,1), selected_members(1,2), &
                                                selected_members(1,3), c_axis, tilt_angle, V, A11, B11, C11, &
                                                D11, E11, F11, best_q, coord_value, best_psi_display_rad, &
                                                best_psi_root_rad, best_two_theta_deg, member_valid)
        else if (best_member_idx > 0) then
            selected_count = 1
            selected_supported = 0
            selected_members(1, :) = members(best_member_idx, :)
            unit_residual = best_residual
            valid = .true.
        end if
    end subroutine evaluate_family_candidate

    subroutine pick_best_singleton_from_family(observed_idx, member_count, members, c_axis, tilt_angle, V, &
                                               A11, B11, C11, D11, E11, F11, best_h, best_k, best_l, &
                                               best_q, best_psi_display_rad, best_psi_root_rad, best_two_theta_deg, &
                                               best_residual, valid)
        integer, intent(in) :: observed_idx, member_count
        integer, intent(in) :: members(4, 3)
        integer, intent(out) :: best_h, best_k, best_l
        real*8, intent(in) :: c_axis, tilt_angle, V, A11, B11, C11, D11, E11, F11
        real*8, intent(out) :: best_q, best_psi_display_rad, best_psi_root_rad, best_two_theta_deg
        real*8, intent(out) :: best_residual
        logical, intent(out) :: valid

        integer :: member_idx
        real*8 :: q_value, coord_value, psi_display_rad, psi_root_rad, two_theta_deg, residual
        logical :: member_valid

        best_h = 0
        best_k = 0
        best_l = 0
        best_q = 0.0d0
        best_psi_display_rad = 0.0d0
        best_psi_root_rad = 0.0d0
        best_two_theta_deg = 0.0d0
        best_residual = 1.0d10
        valid = .false.

        do member_idx = 1, member_count
            call compute_reflection_coordinates(members(member_idx, 1), members(member_idx, 2), &
                                                members(member_idx, 3), c_axis, tilt_angle, V, &
                                                A11, B11, C11, D11, E11, F11, q_value, coord_value, &
                                                psi_display_rad, psi_root_rad, two_theta_deg, member_valid)
            if (.not. member_valid) cycle

            residual = abs(q_value - value1(observed_idx)) * e3 + abs(coord_value - value(observed_idx)) * e2 + V / e4
            if (residual < best_residual) then
                best_residual = residual
                best_h = members(member_idx, 1)
                best_k = members(member_idx, 2)
                best_l = members(member_idx, 3)
                best_q = q_value
                best_psi_display_rad = psi_display_rad
                best_psi_root_rad = psi_root_rad
                best_two_theta_deg = two_theta_deg
                valid = .true.
            end if
        end do
    end subroutine pick_best_singleton_from_family

    subroutine set_family_assignment(observed_idx, representative_h, representative_k, representative_l, &
                                     q_value, psi_display_rad, psi_root_rad, volume_value, member_count, &
                                     supported, members, unit_residual, unit_spread)
        integer, intent(in) :: observed_idx, representative_h, representative_k, representative_l
        integer, intent(in) :: member_count, supported
        integer, intent(in) :: members(4, 3)
        real*8, intent(in) :: q_value, psi_display_rad, psi_root_rad, volume_value
        real*8, intent(in) :: unit_residual, unit_spread

        Miller_trans(observed_idx, 1) = representative_h
        Miller_trans(observed_idx, 2) = representative_k
        Miller_trans(observed_idx, 3) = representative_l
        Miller_trans(observed_idx, 4) = q_value
        Miller_trans(observed_idx, 5) = psi_display_rad
        Miller_trans(observed_idx, 6) = psi_root_rad
        Miller_trans(observed_idx, 7) = volume_value
        family_member_count(observed_idx) = member_count
        family_supported(observed_idx) = supported
        family_key(observed_idx, 1) = abs(representative_h)
        family_key(observed_idx, 2) = abs(representative_k)
        family_key(observed_idx, 3) = representative_l
        family_members(observed_idx, :, :) = members(:, :)
        family_residual_raw(observed_idx) = unit_residual
        family_spread_raw(observed_idx) = unit_spread
    end subroutine set_family_assignment

    function int_to_text(value) result(text)
        integer, intent(in) :: value
        character(len=32) :: text
        write(text, '(I0)') value
    end function int_to_text

    function real_to_text(value) result(text)
        real*8, intent(in) :: value
        character(len=64) :: text
        write(text, '(ES24.16E3)') value
    end function real_to_text

    ! write_family_artifact and clear_family_artifact removed — no longer used

    subroutine error_cal_initial(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real(kind=8), intent(inout) :: parm(:)

        integer :: a1, b1, c1
        integer :: k, merge_mode
        integer :: current_member_count, current_supported
        integer :: current_members(4, 3), candidate_member_count, candidate_supported
        integer :: candidate_members(4, 3)

        real(kind=8) :: a, b, c, alpha, beta, gamma
        real(kind=8) :: V
        real(kind=8) :: A11, B11, C11, D11, E11, F11
        real(kind=8) :: q_value, coord_value, psi_display_rad, psi_root_rad, two_theta_deg
        real(kind=8), parameter :: pi = 3.14159265358979323846d0
        real(kind=8) :: tilt_angle, error_mid, unit_residual
        real(kind=8) :: current_V
        logical :: valid

        character(len=512) :: filename_6

        filename_6 = 'FullMiller.txt'
        open(unit=6, file=filename_6, status='unknown', action='write')
        write(6, *) 'H K L q(A-1) psi(degree) psi-root(degree) 2theta(degree)'

        tilt_angle = 0.0d0
        if (tilt_check == 1) then
            tilt_angle = parm(7) * pi / 180.0d0
        end if

        a = parm(1)
        b = parm(2)
        c = parm(3)
        alpha = parm(4) * pi / 180.0d0
        beta = parm(5) * pi / 180.0d0
        gamma = parm(6) * pi / 180.0d0
        call determine_symmetry_merge_mode(alpha * 180.0d0 / pi, beta * 180.0d0 / pi, gamma * 180.0d0 / pi, merge_mode)

        V = a * b * c * (1.0d0 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + &
            2.0d0 * cos(alpha) * cos(beta) * cos(gamma))**0.5d0
        if (isnan(V) .or. V < 0.01d0) then
            V = 10000000.0d0
        end if

        A11 = b**2 * c**2 * sin(alpha)**2
        B11 = a**2 * c**2 * sin(beta)**2
        C11 = a**2 * b**2 * sin(gamma)**2
        D11 = a * b * c**2 * (cos(alpha) * cos(beta) - cos(gamma))
        E11 = a**2 * b * c * (cos(beta) * cos(gamma) - cos(alpha))
        F11 = a * b**2 * c * (cos(gamma) * cos(alpha) - cos(beta))

        max_h1 = 10
        max_k1 = 10
        max_l1 = 30

        if (allocated(min_error_list)) deallocate(min_error_list)
        allocate(min_error_list(diffraction_num))

        min_error_list = 1.0d10
        Miller_trans(:, :) = 0.0d0
        Miller_trans(:, 1) = 1
        call reset_family_state(diffraction_num)

        current_V = V

        do c1 = 0, max_l1
            do b1 = -max_k1, max_k1
                do a1 = -max_h1, max_h1
                    if (a1 == 0 .and. b1 == 0 .and. c1 == 0) cycle

                    ! l=0: (h,k,0) ≡ (-h,-k,0) — skip one half to avoid duplicate
                    if (c1 == 0 .and. a1 < 0) cycle

                    call compute_reflection_coordinates(a1, b1, c1, c, tilt_angle, V, A11, B11, C11, D11, E11, F11, &
                                                        q_value, coord_value, psi_display_rad, psi_root_rad, &
                                                        two_theta_deg, valid)
                    if (.not. valid) cycle
                    if (psi_root_rad * 180.0d0 / pi < -99.0d0 .or. q_value > 6.0d0) cycle

                    write(6, *) a1, b1, c1, q_value, psi_display_rad * 180.0d0 / pi, &
                                psi_root_rad * 180.0d0 / pi, two_theta_deg

                    if (sym_stat == 1 .and. merge_mode /= 0) then
                        if (merge_mode == 1) then
                            if (a1 < 0) cycle
                            if (a1 == 0 .and. b1 < 0) cycle
                        else if (merge_mode == 2) then
                            if (a1 < 0) cycle
                        else if (merge_mode == 3) then
                            if (b1 < 0) cycle
                        end if

                        call build_family_bucket(abs(a1), abs(b1), c1, merge_mode, &
                                                 candidate_member_count, candidate_supported, candidate_members)
                        do k = 1, diffraction_num
                            call evaluate_family_candidate(k, candidate_member_count, candidate_members, c, tilt_angle, V, &
                                                           A11, B11, C11, D11, E11, F11, current_member_count, &
                                                           current_supported, current_members, q_value, psi_display_rad, &
                                                           psi_root_rad, two_theta_deg, unit_residual, valid)
                            if (.not. valid) cycle
                            if (unit_residual < min_error_list(k)) then
                                min_error_list(k) = unit_residual
                                call set_family_assignment(k, a1, b1, c1, q_value, psi_display_rad, psi_root_rad, &
                                                            current_V, current_member_count, current_supported, &
                                                            current_members, unit_residual, 0.0d0)
                            end if
                        end do
                    else
                        do k = 1, diffraction_num
                            if (level == 1) then
                                error_mid = abs(q_value - value1(k)) * e3 + &
                                            abs(psi_display_rad * 180.0d0 / pi - value(k)) * e2
                            else
                                error_mid = abs(q_value - value1(k)) * e3 + abs(dble(c1) / c - value(k)) * e2
                            end if

                            if (error_mid < min_error_list(k)) then
                                min_error_list(k) = error_mid
                                current_members(:, :) = 0
                                current_members(1, :) = (/ a1, b1, c1 /)
                                call set_family_assignment(k, a1, b1, c1, q_value, psi_display_rad, psi_root_rad, &
                                                           current_V, 1, 0, current_members, error_mid, 0.0d0)
                            end if
                        end do
                    end if
                end do
            end do
        end do

        close(6)
    end subroutine error_cal_initial

    subroutine canonical_hkl(h, k, l, merge_mode, hc, kc, lc)
        implicit none
        integer, intent(in) :: h, k, l, merge_mode
        integer, intent(out) :: hc, kc, lc

        ! 第一层：轴向 Friedel 对（merge_mode 无关，始终生效）
        if (h == 0 .and. k == 0) then
            hc = 0; kc = 0; lc = abs(l)
            return
        else if (h == 0 .and. l == 0) then
            hc = 0; kc = abs(k); lc = 0
            return
        else if (k == 0 .and. l == 0) then
            hc = abs(h); kc = 0; lc = 0
            return
        end if

        ! 第二层：l=0 面内反射（merge_mode 感知）
        if (l == 0) then
            select case (merge_mode)
            case (1, 2, 3)
                ! 正交(1) / alpha-unique(2) / beta-unique(3)：h 和 k 可独立取 abs
                hc = abs(h); kc = abs(k); lc = 0
            case (4)
                ! gamma-unique：2-fold 沿 c 轴仅产生 (h,k,0)~(-h,-k,0)
                if (h < 0) then
                    hc = -h; kc = -k; lc = 0
                else
                    hc = h; kc = k; lc = 0
                end if
            case default
                ! merge_mode=0（精确匹配 / 无对称）：保留原有 Friedel 规则
                if (h < 0) then
                    hc = -h; kc = -k; lc = 0
                else
                    hc = h; kc = k; lc = 0
                end if
            end select
            return
        end if

        ! 第三层：l /= 0 时的晶系对称（两步归一：独立abs是错的，符号联动）
        select case (merge_mode)
        case (1)
            ! 正交: 三个2-fold轴，所有符号独立翻转 → 独立abs正确
            hc = abs(h); kc = abs(k); lc = abs(l)
        case (2)
            ! α-unique (unique axis a): 2-fold绕a → (h,k,l)↔(h,-k,-l)
            ! 两步归一: ① Friedel(全翻)使h≥0 ② 2-fold(翻k,l)使k≥0
            hc = h; kc = k; lc = l
            if (hc < 0) then
                hc = -hc; kc = -kc; lc = -lc   ! Friedel
            end if
            if (kc < 0 .or. (kc == 0 .and. lc < 0)) then
                kc = -kc; lc = -lc              ! 2-fold about a
            end if
        case (3)
            ! β-unique (unique axis b): 2-fold绕b → (h,k,l)↔(-h,k,-l)
            ! 两步归一: ① Friedel(全翻)使k≥0 ② 2-fold(翻h,l)使h≥0
            hc = h; kc = k; lc = l
            if (kc < 0) then
                hc = -hc; kc = -kc; lc = -lc   ! Friedel
            end if
            if (hc < 0 .or. (hc == 0 .and. lc < 0)) then
                hc = -hc; lc = -lc              ! 2-fold about b
            end if
        case (4)
            ! γ-unique (unique axis c): 2-fold绕c → (h,k,l)↔(-h,-k,l)
            ! 两步归一: ① 2-fold(翻h,k)使l≥0 ② Friedel(翻h,k)使h≥0
            hc = h; kc = k; lc = l
            if (lc < 0) then
                hc = -hc; kc = -kc; lc = -lc   ! 2-fold about c
            end if
            if (hc < 0 .or. (hc == 0 .and. kc < 0)) then
                hc = -hc; kc = -kc              ! Friedel
            end if
        case default
            ! No symmetry: exact match
            hc = h; kc = k; lc = l
        end select
    end subroutine

    subroutine error_cal_dedup(diffraction_num, parm)
        use fitting_module
        implicit none
        integer, intent(in) :: diffraction_num
        real*8, intent(in) :: parm(:)

        integer :: i, j, dl
        integer :: merge_mode
        integer :: canonical_peak(maxdata, 3)
        logical :: conflict_flag(maxdata), is_loser(maxdata)
        integer :: h, k, l, l0
        integer :: best_h, best_k, best_l
        integer :: hc, kc, lc, hc2, kc2, lc2
        real*8 :: best_q, best_psi_display, best_psi_root, psi_root_val
        real*8 :: current_error, best_error
        real*8 :: a, b, c, alpha, beta, gamma, V
        real*8 :: A11, B11, C11, D11, E11, F11
        real*8 :: d, theta, q, PHI, d1, y1, PHI_asin
        real*8 :: tilt_angle_rad
        real*8, parameter :: pi = 3.14159265358979323846d0

        if (diffraction_num <= 1) return

        ! 保存原始 Miller 指数（dedup 前）
        do i = 1, diffraction_num
            miller_original(i, 1:3) = Miller_trans(i, 1:3)
        end do
        dedup_loser(1:diffraction_num) = 0

        a = parm(1)
        b = parm(2)
        c = parm(3)
        alpha = parm(4) * pi / 180.0d0
        beta = parm(5) * pi / 180.0d0
        gamma = parm(6) * pi / 180.0d0

        call determine_symmetry_merge_mode(alpha * 180.0d0 / pi, beta * 180.0d0 / pi, gamma * 180.0d0 / pi, merge_mode)

        ! sym_stat=0 时未开启对称归正，dedup 不应使用 canonical 等价。
        ! dedup_sym_mode 不影响 merge_mode — 只有 sym_stat=1 时才启用对称感知的唯一指派。
        if (sym_stat == 0) merge_mode = 0

        V = a * b * c * (1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 + 2*cos(alpha)*cos(beta)*cos(gamma))**0.5
        if (isnan(V) .or. V < 0.01d0) V = 10000000.0d0

        A11 = b**2 * c**2 * sin(alpha)**2
        B11 = a**2 * c**2 * sin(beta)**2
        C11 = a**2 * b**2 * sin(gamma)**2
        D11 = a * b * c**2 * (cos(alpha)*cos(beta) - cos(gamma))
        E11 = a**2 * b * c * (cos(beta)*cos(gamma) - cos(alpha))
        F11 = a * b**2 * c * (cos(gamma)*cos(alpha) - cos(beta))

        tilt_angle_rad = 0.0d0
        if (tilt_check == 1) then
            tilt_angle_rad = parm(7) * pi / 180.0d0
        end if

        do i = 1, diffraction_num
            h = nint(Miller_trans(i, 1))
            k = nint(Miller_trans(i, 2))
            l = nint(Miller_trans(i, 3))
            call canonical_hkl(h, k, l, merge_mode, &
                               canonical_peak(i, 1), canonical_peak(i, 2), canonical_peak(i, 3))
        end do

        conflict_flag(1:diffraction_num) = .false.
        is_loser(1:diffraction_num) = .false.

        do i = 1, diffraction_num
            if (conflict_flag(i)) cycle
            do j = i + 1, diffraction_num
                if (conflict_flag(j)) cycle
                if (canonical_peak(i, 1) == canonical_peak(j, 1) .and. &
                    canonical_peak(i, 2) == canonical_peak(j, 2) .and. &
                    canonical_peak(i, 3) == canonical_peak(j, 3)) then
                    conflict_flag(i) = .true.
                    conflict_flag(j) = .true.
                    if (min_error_list(i) <= min_error_list(j)) then
                        is_loser(j) = .true.
                        dedup_loser(j) = 1
                    else
                        is_loser(i) = .true.
                        dedup_loser(i) = 1
                    end if
                end if
            end do
        end do

        if (.not. any(conflict_flag(1:diffraction_num))) return

        do i = 1, diffraction_num
            if (.not. is_loser(i)) cycle

            l0 = nint(Miller_trans(i, 3))
            best_error = 1.0d30
            best_h = nint(Miller_trans(i, 1))
            best_k = nint(Miller_trans(i, 2))
            best_l = l0

            do h = -max_h1, max_h1
                do k = -max_k1, max_k1
                    do dl = -1, 1
                        l = l0 + dl
                        if (h == 0 .and. k == 0 .and. l == 0) cycle

                        do j = 1, diffraction_num
                            if (j == i .or. is_loser(j)) cycle
                            if (nint(Miller_trans(j, 1)) == h .and. &
                                nint(Miller_trans(j, 2)) == k .and. &
                                nint(Miller_trans(j, 3)) == l) then
                                go to 150
                            end if
                            call canonical_hkl(nint(Miller_trans(j,1)), nint(Miller_trans(j,2)), &
                                               nint(Miller_trans(j,3)), merge_mode, hc, kc, lc)
                            call canonical_hkl(h, k, l, merge_mode, hc2, kc2, lc2)
                            if (hc == hc2 .and. kc == kc2 .and. lc == lc2) then
                                go to 150
                            end if
                        end do

                        d = 1.0d0 / sqrt( &
                            (h**2 * A11 + k**2 * B11 + l**2 * C11 + 2*h*k*D11 + 2*k*l*E11 + 2*h*l*F11) / V**2 &
                        )
                        if (isnan(d) .or. d <= 0.0d0) cycle
                        theta = asin(wavelength / (2.0d0 * d))
                        if (theta /= theta) cycle
                        q = (1.0d0 / d) * 2.0d0 * pi

                        d1 = 1.0d0 / wavelength * sin(2.0d0 * theta)
                        if (l == 0) then
                            y1 = 0.0d0
                        else
                            y1 = dble(l) / c
                        end if

                        if (tilt_check == 1) then
                            PHI_asin = (y1 / cos(tilt_angle_rad) + 1.0d0 / d * sin(theta) * tan(tilt_angle_rad)) / d1
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

                        ! Root psi (uncorrected) — always asin(y1/d1)
                        if (y1 / d1 > 1.0d0 .or. y1 / d1 < -1.0d0) then
                            psi_root_val = pi / 2.0d0
                        else
                            psi_root_val = asin(y1 / d1)
                        end if

                        if (level == 1) then
                            current_error = abs(q - value1(i)) * e3 + abs(PHI * 180.0d0 / pi - value(i)) * e2
                        else
                            current_error = abs(q - value1(i)) * e3 + abs(dble(l) / c - value(i)) * e2
                        end if

                        if (current_error < best_error) then
                            best_error = current_error
                            best_h = h
                            best_k = k
                            best_l = l
                            best_q = q
                            best_psi_display = PHI
                            best_psi_root = psi_root_val
                        end if
150                     continue
                    end do
                end do
            end do

            Miller_trans(i, 1) = best_h
            Miller_trans(i, 2) = best_k
            Miller_trans(i, 3) = best_l
            Miller_trans(i, 4) = best_q
            Miller_trans(i, 5) = best_psi_display
            Miller_trans(i, 6) = best_psi_root
            Miller_trans(i, 7) = V
            min_error_list(i) = best_error
        end do

        if (allocated(min_error_list)) deallocate(min_error_list)

    end subroutine

end module calhkl


program LMfit
    use fitting_module
    use calhkl
    implicit real*8 (a-h, o-z)
    integer :: nparm
    integer :: diffraction_num, num_cell
    real*8, allocatable :: parm(:)
    real*8 fiterr(maxdata), fitval(maxdata), fitval1(maxdata)
    character(len=512) :: filename_input, filename_cell, filename_dif
    character(len=512) :: input_type, input_type2, input_type3
    character(len=512) :: filename1, filename2, filename3, filename_5
    real*8, allocatable :: cell_parameter(:, :), error_total(:)
    character c80tmp*80
    real*8 :: tilt_angle
    integer :: io_status
    real*8, allocatable :: reflection_position(:, :), reflection_position1(:, :)

    tol = 1D-7
    maxcall = 5000

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
        write(*, *) 'wrong input_type，choosen -i,-input,-c,-crystal,-d,-diffrac'
        stop
    end if

    open(unit=1, file=filename_input, status='old', action='read')
    do i = 1, 32
        if (i == 1) then
            read(1, *) wavelength
        else if (i == 13) then
            read(1, *) level
        else if (i == 15) then
            read(1, *) e2
        else if (i == 16) then
            read(1, *) e3
        else if (i == 17) then
            read(1, *) e4
        else if (i == 18) then
            read(1, *) x1
        else if (i == 23) then
            read(1, *) sym_stat
        else if (i == 24) then
            read(1, *) sym_e
        else if (i == 20) then
            read(1, *) sym_tq
            if (sym_tq <= 0.0d0) sym_tq = 0.02d0
        else if (i == 21) then
            read(1, *) sym_ta
            if (sym_ta <= 0.0d0) sym_ta = 1.0d0
        else if (i == 27) then
            read(1, *) tilt_check
        else if (i == 30) then
            read(1, *, iostat=io_status) deduplicate_enabled
            if (io_status /= 0) deduplicate_enabled = 0
        else if (i == 31) then
            read(1, *, iostat=io_status) dedup_penalty
            if (io_status /= 0 .or. dedup_penalty < 1.0d0) dedup_penalty = 1.0d0
        else if (i == 32) then
            read(1, *, iostat=io_status) dedup_sym_mode
            if (io_status /= 0) dedup_sym_mode = 0
        else
            read(1, *)
        end if
    end do

    num_cell = 1
    close(1)

    open(10, file=filename_dif, status='old')
    diffraction_num = 0
    do while (.true.)
        read(10, '(a)', iostat=ierror) c80tmp
        if (c80tmp == ' ' .or. ierror /= 0) exit
        diffraction_num = diffraction_num + 1
        read(c80tmp, *) value1(diffraction_num), value(diffraction_num)
    end do
    close(10)

    open(unit=2, file=filename_cell, status='old', action='read')
    do i = 1, num_cell
        if (tilt_check == 1) then
            allocate(cell_parameter(num_cell, 7))
            read(2, *) cell_parameter(i, 1), cell_parameter(i, 2), cell_parameter(i, 3), &
                       cell_parameter(i, 4), cell_parameter(i, 5), cell_parameter(i, 6), cell_parameter(i, 7)
            nparm = 7
        else
            allocate(cell_parameter(num_cell, 6))
            read(2, *) cell_parameter(i, 1), cell_parameter(i, 2), cell_parameter(i, 3), &
                       cell_parameter(i, 4), cell_parameter(i, 5), cell_parameter(i, 6)
            nparm = 6
        end if
    end do
    close(2)

    allocate(error_total(num_cell))
    allocate(parm(nparm))
    allocate(reflection_position(10000, 5))
    allocate(reflection_position1(10000, 6))

    do i = 1, num_cell
        parm(1) = cell_parameter(i, 1)
        parm(2) = cell_parameter(i, 2)
        parm(3) = cell_parameter(i, 3)
        parm(4) = cell_parameter(i, 4)
        parm(5) = cell_parameter(i, 5)
        parm(6) = cell_parameter(i, 6)
        if (tilt_check == 1) then
            parm(7) = cell_parameter(i, 7)
        end if

        call error_cal_initial(diffraction_num, parm)
        if (deduplicate_enabled == 1) then
            call error_cal_dedup(diffraction_num, parm)
        end if
    end do

    filename_5 = 'outputMiller.txt'
    open(unit=5, file=filename_5, status='unknown', action='write')

    if (tilt_check == 1) then
        write(5, *) 'H K L q psi psi-root'
        do i = 1, diffraction_num
            write(5, *) Miller_trans(i, 1), Miller_trans(i, 2), Miller_trans(i, 3), Miller_trans(i, 4), &
                        Miller_trans(i, 5) * 180.0d0 / 3.141592653589d0, &
                        Miller_trans(i, 6) * 180.0d0 / 3.141592653589d0
        end do
        write(5, *) 'volume:', Miller_trans(1, 7)
    else
        write(5, *) 'H K L q psi'
        do i = 1, diffraction_num
            write(5, *) Miller_trans(i, 1), Miller_trans(i, 2), Miller_trans(i, 3), Miller_trans(i, 4), &
                        Miller_trans(i, 5) * 180.0d0 / 3.141592653589d0
        end do
        write(5, *) 'volume:', Miller_trans(1, 7)
    end if

    close(5)

    ! 输出峰独占冲突报告（复用 error_cal_dedup 的 dedup_loser 标记）
    if (deduplicate_enabled == 1) then
        open(unit=6, file='dedup_conflicts.txt', status='unknown', action='write')
        write(6, *) '# Peak Deduplication Conflict Report'
        write(6, *) '# Peak  Original_HKL  ->  Final_HKL    Status'
        write(6, *) '#----------------------------------------------'
        do i = 1, diffraction_num
            if (dedup_loser(i) == 1) then
                write(6, '(I4,2X,I4,1X,I4,1X,I4,2X,A3,2X,I4,1X,I4,1X,I4,2X,A6)') &
                    i, nint(miller_original(i,1)), nint(miller_original(i,2)), nint(miller_original(i,3)), &
                    ' ->', nint(Miller_trans(i,1)), nint(Miller_trans(i,2)), nint(Miller_trans(i,3)), &
                    'REMAP'
            else
                write(6, '(I4,2X,I4,1X,I4,1X,I4,2X,A3,2X,I4,1X,I4,1X,I4,2X,A6)') &
                    i, nint(miller_original(i,1)), nint(miller_original(i,2)), nint(miller_original(i,3)), &
                    ' ->', nint(Miller_trans(i,1)), nint(Miller_trans(i,2)), nint(Miller_trans(i,3)), &
                    'KEEP'
            end if
        end do
        close(6)
    end if

    ! families artifact removed — no longer generated

    write(*, *) ' '
end program
