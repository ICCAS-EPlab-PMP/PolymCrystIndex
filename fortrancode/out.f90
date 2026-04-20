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

    subroutine build_family_bucket(abs_h, abs_k, l_value, member_count, supported, members)
        integer, intent(in) :: abs_h, abs_k, l_value
        integer, intent(out) :: member_count, supported
        integer, intent(out) :: members(4, 3)

        members(:, :) = 0
        member_count = 1
        supported = 0

        if (abs_h == 0 .and. abs_k == 0) then
            members(1, :) = (/ 0, 0, l_value /)
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

        unit_spread = calculate_family_spread(member_count, q_values, coord_values)
        unit_residual = member_error_sum / dble(member_count) + unit_spread
    end subroutine calculate_family_unit_residual

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

    subroutine write_family_artifact(diffraction_num)
        integer, intent(in) :: diffraction_num
        integer :: i, member_idx
        character(len=64) :: observed_idx_text, supported_text, member_count_text
        character(len=64) :: key_h_text, key_k_text, key_l_text
        character(len=64) :: residual_text, spread_text
        character(len=64) :: member_h_text, member_k_text, member_l_text
        character(len=256) :: member_json
        character(len=1024) :: members_block
        character(len=2048) :: line

        open(unit=8, file='outputMillerFamilies.jsonl', status='unknown', action='write')

        do i = 1, diffraction_num
            observed_idx_text = trim(int_to_text(i))
            supported_text = trim(int_to_text(family_supported(i)))
            member_count_text = trim(int_to_text(family_member_count(i)))
            key_h_text = trim(int_to_text(family_key(i, 1)))
            key_k_text = trim(int_to_text(family_key(i, 2)))
            key_l_text = trim(int_to_text(family_key(i, 3)))
            residual_text = trim(real_to_text(family_residual_raw(i)))
            spread_text = trim(real_to_text(family_spread_raw(i)))

            members_block = ''
            do member_idx = 1, family_member_count(i)
                member_h_text = trim(int_to_text(family_members(i, member_idx, 1)))
                member_k_text = trim(int_to_text(family_members(i, member_idx, 2)))
                member_l_text = trim(int_to_text(family_members(i, member_idx, 3)))
                member_json = '[' // trim(member_h_text) // ',' // trim(member_k_text) // ',' // trim(member_l_text) // ']'
                if (member_idx > 1) then
                    members_block = trim(members_block) // ','
                end if
                members_block = trim(members_block) // trim(member_json)
            end do

            line = '{"observed_peak_index":' // trim(observed_idx_text) // &
                   ',"family_supported":' // trim(supported_text) // &
                   ',"family_key":[' // trim(key_h_text) // ',' // trim(key_k_text) // ',' // trim(key_l_text) // ']' // &
                   ',"member_count":' // trim(member_count_text) // &
                   ',"member_hkls":[' // trim(members_block) // ']' // &
                   ',"family_residual":' // trim(residual_text) // &
                   ',"intra_family_spread":' // trim(spread_text) // '}'
            write(8, '(A)') trim(line)
        end do

        close(8)
    end subroutine write_family_artifact

    subroutine clear_family_artifact()
        logical :: file_exists

        inquire(file='outputMillerFamilies.jsonl', exist=file_exists)
        if (file_exists) then
            open(unit=9, file='outputMillerFamilies.jsonl', status='old', action='readwrite')
            close(9, status='delete')
        end if
    end subroutine clear_family_artifact

    subroutine error_cal_initial(diffraction_num, parm)
        integer, intent(in) :: diffraction_num
        real(kind=8), intent(inout) :: parm(:)

        integer :: a1, b1, c1
        integer :: k, i
        integer :: current_member_count, current_supported
        integer :: current_members(4, 3)

        real(kind=8) :: a, b, c, alpha, beta, gamma
        real(kind=8) :: V
        real(kind=8) :: A11, B11, C11, D11, E11, F11
        real(kind=8) :: q_value, coord_value, psi_display_rad, psi_root_rad, two_theta_deg
        real(kind=8), parameter :: pi = 3.14159265358979323846d0
        real(kind=8) :: tilt_angle, error_mid, unit_residual, unit_spread
        real(kind=8) :: current_V
        real(kind=8), allocatable :: min_error_list(:)
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

                    call compute_reflection_coordinates(a1, b1, c1, c, tilt_angle, V, A11, B11, C11, D11, E11, F11, &
                                                        q_value, coord_value, psi_display_rad, psi_root_rad, &
                                                        two_theta_deg, valid)
                    if (.not. valid) cycle
                    if (psi_root_rad * 180.0d0 / pi < -99.0d0 .or. q_value > 6.0d0) cycle

                    write(6, *) a1, b1, c1, q_value, psi_display_rad * 180.0d0 / pi, &
                                psi_root_rad * 180.0d0 / pi, two_theta_deg

                    if (sym_stat == 1) then
                        if (a1 < 0) cycle
                        if (a1 == 0 .and. b1 < 0) cycle

                        call build_family_bucket(abs(a1), abs(b1), c1, current_member_count, current_supported, current_members)
                        do k = 1, diffraction_num
                            call calculate_family_unit_residual(k, current_member_count, current_members, c, tilt_angle, V, &
                                                                A11, B11, C11, D11, E11, F11, unit_residual, unit_spread, valid)
                            if (.not. valid) cycle
                            if (unit_residual < min_error_list(k)) then
                                min_error_list(k) = unit_residual
                                call set_family_assignment(k, a1, b1, c1, q_value, psi_display_rad, psi_root_rad, &
                                                           current_V, current_member_count, current_supported, &
                                                           current_members, unit_residual, unit_spread)
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

        if (allocated(min_error_list)) deallocate(min_error_list)
        close(6)
    end subroutine error_cal_initial

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
    do i = 1, 28
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
        else if (i == 27) then
            read(1, *) tilt_check
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

    if (sym_stat == 1) then
        call write_family_artifact(diffraction_num)
    else
        call clear_family_artifact()
    end if

    write(*, *) ' '
end program
