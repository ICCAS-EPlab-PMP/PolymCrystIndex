"""
Sort Module for POLYCRYSTINDEX
==============================

This module implements the genetic algorithm for sorting and optimizing
unit cell parameters in fiber diffraction analysis.

Main Functions:
    - read_diffraction: Read and sort diffraction data by q-values
    - cell_sort: Sort cell parameters according to diffraction order
    - new_generation: Generate new population using genetic operations

Genetic Algorithm Features:
    - Survival selection
    - Crossover operations
    - Mutation operations
    - Random generation for population diversity

Author: POLYCRYSTINDEX Team
Version: 1.7

Usage:
    python sort.py -i input.txt -c cell.txt -n generation_number
"""

import os
import sys
import random
import math
import time
import argparse
from typing import List, Tuple, Optional, Dict, Any

DIFFERENT_LENGTH = 0.1
DIFFERENT_ANGLE = 0.5


def read_diffraction(diffraction_name: str) -> List[List[float]]:
    """Read and sort diffraction data by q-values.
    
    Reads the diffraction data from file, where each line contains
    q-value and index information. Sorts the data by q-values in
    ascending order.
    
    Args:
        diffraction_name: Path to diffraction data file
        
    Returns:
        List of [q_value, index] pairs sorted by q_value
        
    Raises:
        FileNotFoundError: If diffraction file does not exist
        ValueError: If file format is invalid
        
    Example:
        >>> diffraction = read_diffraction('diffraction.txt')
        >>> print(diffraction[0])
        [0.123, 5]
    """
    diffraction = []
    
    if not os.path.exists(diffraction_name):
        raise FileNotFoundError(f"Diffraction file not found: {diffraction_name}")
    
    try:
        with open(diffraction_name, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip('\n')
                parts = line.split()
                if len(parts) < 1:
                    continue
                try:
                    q_value = float(parts[0])
                    diffraction.append([q_value, line_num])
                except ValueError:
                    raise ValueError(
                        f"Invalid q-value at line {line_num}: {parts[0]}"
                    )
        
        diffraction.sort(key=lambda x: x[0])
        return diffraction
        
    except IOError as e:
        raise IOError(f"Error reading diffraction file: {e}")


def cell_sort(cell_name: str, diffraction_name: str, 
              tilt_stat: int) -> Tuple[List[List[float]], float]:
    """Sort cell parameters according to error values (ascending).
    
    Reads cell parameters from annealing file and error values from
    diffraction.txt, then sorts cells by error (lowest first).
    
    Args:
        cell_name: Path to cell_annealing file (cell parameters)
        diffraction_name: Path to diffraction.txt (error values, one per line)
        tilt_stat: Tilt angle mode flag (1=enabled, 0=disabled)
        
    Returns:
        Tuple of (sorted cell list by error, best_error value)
        
    Raises:
        FileNotFoundError: If files do not exist
    """
    if not os.path.exists(cell_name):
        raise FileNotFoundError(f"Cell file not found: {cell_name}")
    if not os.path.exists(diffraction_name):
        raise FileNotFoundError(f"Error file not found: {diffraction_name}")
    
    try:
        cells_with_errors = []
        
        with open(cell_name, 'r') as f:
            cell_lines = f.readlines()
        
        with open(diffraction_name, 'r') as f:
            error_lines = f.readlines()
        
        num_cells = len(cell_lines)
        
        for i in range(num_cells):
            line = cell_lines[i].strip('\n')
            parts = line.split()
            
            if tilt_stat == 1 and len(parts) >= 7:
                cell_params = [float(parts[0]), float(parts[1]), float(parts[2]), 
                               float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])]
            elif len(parts) >= 6:
                cell_params = [float(parts[0]), float(parts[1]), float(parts[2]), 
                               float(parts[3]), float(parts[4]), float(parts[5])]
            else:
                continue
            
            if i < len(error_lines):
                try:
                    error_val = float(error_lines[i].strip())
                except ValueError:
                    error_val = float('inf')
            else:
                error_val = float('inf')
            
            cells_with_errors.append((error_val, cell_params))
        
        cells_with_errors.sort(key=lambda x: x[0])
        
        cell = [c[1] for c in cells_with_errors]
        
        best_error = cells_with_errors[0][0] if cells_with_errors else float('inf')
        
        return cell, best_error
        
    except IOError as e:
        raise IOError(f"Error reading cell file: {e}")
    except IndexError as e:
        raise IndexError(f"Cell file format error: {e}")


def _is_duplicate_cell(cell1: List, cell2: List) -> bool:
    """Check if two cell parameter sets are duplicates.
    
    Compares cell parameters using predefined thresholds for
    length (0.1 Angstrom) and angle (0.5 degree) differences.
    
    Args:
        cell1: First cell parameter list
        cell2: Second cell parameter list
        
    Returns:
        True if cells are duplicates, False otherwise
    """
    length_diff = DIFFERENT_LENGTH
    angle_diff = DIFFERENT_ANGLE
    
    is_length_similar = (
        abs(float(cell1[0]) - float(cell2[0])) < length_diff and
        abs(float(cell1[1]) - float(cell2[1])) < length_diff and
        abs(float(cell1[2]) - float(cell2[2])) < length_diff
    )
    
    angle1_ok = abs(float(cell1[3]) - float(cell2[3])) < angle_diff or \
                abs(180 - float(cell1[3]) - float(cell2[3])) < angle_diff
    angle2_ok = abs(float(cell1[4]) - float(cell2[4])) < angle_diff or \
                abs(180 - float(cell1[4]) - float(cell2[4])) < angle_diff
    angle3_ok = abs(float(cell1[5]) - float(cell2[5])) < angle_diff or \
                abs(180 - float(cell1[5]) - float(cell2[5])) < angle_diff
    
    return is_length_similar and angle1_ok and angle2_ok and angle3_ok


def new_generation(cell: List[List[float]], survive: int, cross: int,
                   mutation: int, new_random: int, c_axis: float,
                   population_size: int, all_min: List[str],
                   all_max: List[str], tilt_stat: int) -> List[List[float]]:
    """Generate new population using genetic algorithm operations.
    
    Creates a new generation of unit cell parameters through:
    1. Survival selection (best individuals)
    2. Crossover (combining two parent cells)
    3. Mutation (random changes to parameters)
    4. Random generation (new random individuals)
    
    Args:
        cell: Current cell population sorted by fitness
        survive: Number of survivors from current generation
        cross: Number of crossover individuals to create
        mutation: Number of mutant individuals to create
        new_random: Number of new random individuals
        c_axis: Fixed c-axis value (0 = variable)
        population_size: Maximum population size
        all_min: Minimum values for all parameters [a,b,c,alpha,beta,gamma]
        all_max: Maximum values for all parameters
        tilt_stat: Tilt angle mode flag (1=enabled)
        
    Returns:
        New population of cell parameters
    """
    cell_size = len(cell)
    
    if float(survive) * 1.2 > float(cell_size):
        survive = int(float(cell_size) / 1.2)
    if float(survive) > float(cell_size):
        new_random = int(population_size - survive - cross - mutation)
    
    cell_mid = []
    cell_mid1 = []
    cell_all = []
    
    for i in range(int(survive * 1.2)):
        if tilt_stat == 1:
            cell_mid.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5]),
                float(cell[i][6])
            ])
        else:
            cell_mid.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5])
            ])
    
    for i in range(int(survive * 1.2)):
        if tilt_stat == 1:
            cell_mid1.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5]),
                float(cell[i][6])
            ])
        else:
            cell_mid1.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5])
            ])
    
    cell_all = _generate_survivors(cell, survive, tilt_stat)
    
    cell_all = _generate_crossovers(
        cell_mid, cross, c_axis, tilt_stat, survive, cell_all
    )
    
    cell_all = _generate_mutations(
        cell_mid1, mutation, c_axis, tilt_stat, survive, cell_all
    )
    
    cell_all = _generate_random_cells(
        cell_all, new_random, c_axis, population_size,
        all_min, all_max, tilt_stat
    )
    
    cell_all = _validate_and_fix_cells(
        cell_all, all_min, all_max, c_axis, tilt_stat
    )
    
    return cell_all


def _generate_survivors(cell: List[List[float]], survive: int,
                         tilt_stat: int) -> List[List[float]]:
    """Generate surviving individuals for next generation."""
    survivors = []
    for i in range(survive):
        if tilt_stat == 1:
            survivors.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5]),
                float(cell[i][6])
            ])
        else:
            survivors.append([
                float(cell[i][0]), float(cell[i][1]), float(cell[i][2]),
                float(cell[i][3]), float(cell[i][4]), float(cell[i][5])
            ])
    return survivors


def _generate_crossovers(cell_mid: List[List[float]], cross: int,
                          c_axis: float, tilt_stat: int, survive: int,
                          cell_all: List[List[float]]) -> List[List[float]]:
    """Generate crossover individuals through genetic combination."""
    for i in range(cross):
        change1 = random.randint(0, int(1.2 * (survive - 1)))
        change2 = random.randint(0, int(1.2 * (survive - 1)))
        change_num = 3
        
        if c_axis == 0:
            change_list = random.sample([0, 1, 2, 3, 4, 5], change_num)
        elif tilt_stat == 1:
            change_list = random.sample([0, 1, 2, 3, 4, 5, 6], change_num)
        else:
            change_list = random.sample([0, 1, 3, 4, 5], change_num)
        
        for j in range(change_num):
            if change_list[j] in [0, 1]:
                change_list2 = random.randint(0, 1)
                cell_mid[change1][change_list[j]], cell_mid[change2][change_list2] = \
                    cell_mid[change2][change_list2], cell_mid[change1][change_list[j]]
            elif change_list[j] == 2 and c_axis == 0:
                cell_mid[change1][change_list[j]], cell_mid[change2][change_list[j]] = \
                    cell_mid[change2][change_list[j]], cell_mid[change1][change_list[j]]
            elif change_list[j] in [3, 4, 5]:
                change_list2 = random.randint(3, 5)
                cell_mid[change1][change_list[j]], cell_mid[change2][change_list2] = \
                    cell_mid[change2][change_list2], cell_mid[change1][change_list[j]]
            else:
                cell_mid[change1][change_list[j]], cell_mid[change2][change_list[j]] = \
                    cell_mid[change2][change_list[j]], cell_mid[change1][change_list[j]]
        
        for c in range(6):
            if c in [0, 1] or (c == 2 and c_axis == 0):
                add_num1 = random.uniform(-1, 1)
                cell_mid[change1][c] = float(cell_mid[change1][c]) + add_num1 / 4
            elif c in [3, 4, 5]:
                add_num1 = random.uniform(-4, 4)
                cell_mid[change1][c] = cell_mid[change1][c] + add_num1
        
        if tilt_stat == 1:
            cell_all.append([
                cell_mid[change1][0], cell_mid[change1][1], cell_mid[change1][2],
                cell_mid[change1][3], cell_mid[change1][4], cell_mid[change1][5],
                cell_mid[change1][6]
            ])
        else:
            cell_all.append([
                cell_mid[change1][0], cell_mid[change1][1], cell_mid[change1][2],
                cell_mid[change1][3], cell_mid[change1][4], cell_mid[change1][5]
            ])
    
    return cell_all


def _generate_mutations(cell_mid1: List[List[float]], mutation: int,
                         c_axis: float, tilt_stat: int, survive: int,
                         cell_all: List[List[float]]) -> List[List[float]]:
    """Generate mutant individuals through random changes."""
    for i in range(mutation):
        change1 = random.randint(0, survive - 1)
        change_num = 3
        
        if c_axis == 0:
            change_list = random.sample([0, 1, 2, 3, 4, 5], change_num)
        elif tilt_stat == 1:
            change_list = random.sample([0, 1, 2, 3, 4, 5, 6], change_num)
        else:
            change_list = random.sample([0, 1, 3, 4, 5], change_num)
        
        for j in range(change_num):
            add_num = random.uniform(-3, 3)
            if change_list[j] in [0, 1] or (change_list[j] == 2 and c_axis == 0):
                cell_mid1[change1][change_list[j]] = (
                    float(cell_mid1[change1][change_list[j]]) + add_num / 1.5
                )
            elif change_list[j] in [3, 4, 5]:
                cell_mid1[change1][change_list[j]] = (
                    float(cell_mid1[change1][change_list[j]]) + add_num * 2
                )
            else:
                cell_mid1[change1][change_list[j]] = (
                    float(cell_mid1[change1][change_list[j]]) + add_num / 2
                )
        
        if tilt_stat == 1:
            cell_all.append([
                cell_mid1[change1][0], cell_mid1[change1][1], cell_mid1[change1][2],
                cell_mid1[change1][3], cell_mid1[change1][4], cell_mid1[change1][5],
                cell_mid1[change1][6]
            ])
        else:
            cell_all.append([
                cell_mid1[change1][0], cell_mid1[change1][1], cell_mid1[change1][2],
                cell_mid1[change1][3], cell_mid1[change1][4], cell_mid1[change1][5]
            ])
    
    return cell_all


def _generate_random_cells(cell_all: List[List[float]], new_random: int,
                            c_axis: float, population_size: int,
                            all_min: List[str], all_max: List[str],
                            tilt_stat: int) -> List[List[float]]:
    """Generate new random cell parameters."""
    a_min = float(all_min[0])
    b_min = float(all_min[1])
    c_min = float(all_min[2])
    alpha_min = float(all_min[3])
    beta_min = float(all_min[4])
    gamma_min = float(all_min[5])
    
    a_max = float(all_max[0])
    b_max = float(all_max[1])
    c_max = float(all_max[2])
    alpha_max = float(all_max[3])
    beta_max = float(all_max[4])
    gamma_max = float(all_max[5])
    
    for i in range(new_random):
        a = random.uniform(a_min, a_max)
        b = random.uniform(b_min, b_max)
        c = c_axis if c_axis != 0 else random.uniform(c_min, c_max)
        alpha = random.uniform(alpha_min, alpha_max)
        beta = random.uniform(beta_min, beta_max)
        gamma = random.uniform(gamma_min, gamma_max)
        
        if tilt_stat == 1:
            tilt_angle = random.uniform(-10, 10)
            cell_matrix = [a, b, c, alpha, beta, gamma, tilt_angle]
        else:
            tilt_angle = 0.0
            cell_matrix = [a, b, c, alpha, beta, gamma]
        
        cell_all.append(cell_matrix)
    
    if len(cell_all) > population_size:
        cell_all = cell_all[:population_size]
    
    return cell_all


def _validate_and_fix_cells(cell_all: List[List[float]], all_min: List[str],
                              all_max: List[str], c_axis: float,
                              tilt_stat: int) -> List[List[float]]:
    """Validate and fix cell parameters to ensure they are within bounds."""
    a_min = float(all_min[0])
    a_max = float(all_max[0])
    b_min = float(all_min[1])
    b_max = float(all_max[1])
    c_min = float(all_min[2])
    c_max = float(all_max[2])
    alpha_min = float(all_min[3])
    alpha_max = float(all_max[3])
    beta_min = float(all_min[4])
    beta_max = float(all_max[4])
    gamma_min = float(all_min[5])
    gamma_max = float(all_max[5])
    
    for i in range(len(cell_all)):
        if float(cell_all[i][0]) < float(cell_all[i][1]):
            cell_all[i][0], cell_all[i][1] = cell_all[i][1], cell_all[i][0]
            cell_all[i][3], cell_all[i][4] = cell_all[i][4], cell_all[i][3]
        
        if float(cell_all[i][0]) < a_min or float(cell_all[i][0]) > a_max:
            cell_all[i][0] = random.uniform(a_min, a_max)
        if float(cell_all[i][1]) < b_min or float(cell_all[i][1]) > b_max:
            cell_all[i][1] = random.uniform(b_min, b_max)
        if (float(cell_all[i][2]) < c_min or float(cell_all[i][2]) > c_max) and c_axis == 0:
            cell_all[i][2] = random.uniform(c_min, c_max)
        
        if float(cell_all[i][3]) > alpha_max or float(cell_all[i][3]) < alpha_min:
            cell_all[i][3] = random.uniform(alpha_min, alpha_max)
        if float(cell_all[i][4]) > beta_max or float(cell_all[i][4]) < beta_min:
            cell_all[i][4] = random.uniform(beta_min, beta_max)
        if float(cell_all[i][5]) > gamma_max or float(cell_all[i][5]) < gamma_min:
            cell_all[i][5] = random.uniform(gamma_min, gamma_max)
    
    return cell_all


def main():
    """Main entry point for the sort module.
    
    Parses command line arguments and executes the genetic algorithm
    to generate a new population of cell parameters.
    """
    parser = argparse.ArgumentParser(
        description='Sort and optimize unit cell parameters using genetic algorithm'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=None,
        help='Input file path'
    )
    parser.add_argument(
        '-c', '--cell',
        type=str,
        default=None,
        help='Cell file path'
    )
    parser.add_argument(
        '-d', '--diffraction',
        type=str,
        default=None,
        help='Observed diffraction file path'
    )
    parser.add_argument(
        '-n', '--number',
        type=int,
        default=None,
        help='Generation number'
    )
    
    args = parser.parse_args()
    
    if not args.input or not args.cell:
        sys.stderr.write("Error: Both input and cell file paths are required\n")
        sys.exit(1)
    
    inputfile = args.input
    cell_name = args.cell
    
    try:
        with open(inputfile, 'r') as f:
            lines = f.readlines()
        
        population_size = int(lines[3].strip('\n').split()[0])
        survival_rate = float(lines[5].strip('\n').split()[0])
        survive = int(population_size * survival_rate)
        cross_rate = float(lines[6].strip('\n').split()[0])
        cross = int(population_size * cross_rate)
        mutation_rate = float(lines[7].strip('\n').split()[0])
        c_axis = float(lines[10].strip('\n').split()[0])
        
        try:
            all_min = lines[24].strip(' \n').split()
            all_max = lines[25].strip(' \n').split()
            tilt_stat = int(lines[26])
        except (IndexError, ValueError) as e:
            sys.stderr.write(f"Error: Format of max and min values is wrong: {e}\n")
            sys.exit(1)
        
        if survive + cross + int(mutation_rate * population_size) > population_size:
            mutation = population_size - survive - cross
            new_random = 0
        else:
            mutation = int(population_size * mutation_rate)
            new_random = population_size - survive - cross - mutation
        
        workdir = os.getcwd()
        diffraction_name = os.path.abspath(args.diffraction) if args.diffraction else os.path.join(workdir, "diffraction.txt")
        generation = int(args.number)
        
        error_file = os.path.join(workdir, f"error_{generation - 1}.txt")
        
        diffraction = read_diffraction(diffraction_name)
        cell, best_error = cell_sort(cell_name, error_file, tilt_stat)
        
        cell_all = new_generation(
            cell, survive, cross, mutation, new_random,
            c_axis, population_size, all_min, all_max, tilt_stat
        )
        
        while len(cell_all) < population_size:
            a = random.uniform(float(all_min[0]), float(all_max[0]))
            b = random.uniform(float(all_min[1]), float(all_max[1]))
            c = c_axis if c_axis != 0 else random.uniform(float(all_min[2]), float(all_max[2]))
            alpha = random.uniform(float(all_min[3]), float(all_max[3]))
            beta = random.uniform(float(all_min[4]), float(all_max[4]))
            gamma = random.uniform(float(all_min[5]), float(all_max[5]))
            if tilt_stat == 1:
                tilt_angle = random.uniform(-10, 10)
                cell_all.append([a, b, c, alpha, beta, gamma, tilt_angle])
            else:
                cell_all.append([a, b, c, alpha, beta, gamma])
        
        cell_file = open(os.path.join(workdir, 'cell_' + str(generation) + '.txt'), 'w')
        
        if tilt_stat == 1:
            for i in range(len(cell_all)):
                cell_file.write(
                    f"{float(cell_all[i][0]):.4f} {float(cell_all[i][1]):.4f} "
                    f"{float(cell_all[i][2]):.4f} {float(cell_all[i][3]):.4f} "
                    f"{float(cell_all[i][4]):.4f} {float(cell_all[i][5]):.4f} "
                    f"{float(cell_all[i][6]):.4f}\n"
                )
        else:
            for i in range(len(cell_all)):
                cell_file.write(
                    f"{float(cell_all[i][0]):.4f} {float(cell_all[i][1]):.4f} "
                    f"{float(cell_all[i][2]):.4f} {float(cell_all[i][3]):.4f} "
                    f"{float(cell_all[i][4]):.4f} {float(cell_all[i][5]):.4f}\n"
                )
        
        cell_file.close()
        
        error_display = f"{best_error:.2f}" if best_error != float('inf') else "N/A"
        if tilt_stat == 1:
            output_msg = (
                f"THE {generation} step BEST cell parameter now is "
                f"a: {cell_all[0][0]:.2f} b: {cell_all[0][1]:.2f} c: {cell_all[0][2]:.2f} "
                f"alpha: {cell_all[0][3]:.2f} beta: {cell_all[0][4]:.2f} gamma: {cell_all[0][5]:.2f} "
                f"tilt_angle: {cell_all[0][6]:.2f} || Now error is {error_display} "
                f"|| The best generation is {diffraction[0][1]}\n"
            )
        else:
            output_msg = (
                f"THE {generation} step BEST cell parameter now is "
                f"a: {cell_all[0][0]:.2f} b: {cell_all[0][1]:.2f} c: {cell_all[0][2]:.2f} "
                f"alpha: {cell_all[0][3]:.2f} beta: {cell_all[0][4]:.2f} gamma: {cell_all[0][5]:.2f} "
                f"|| Now error is {error_display} "
                f"|| The best generation is {diffraction[0][1]}\n"
            )
        
        sys.stdout.write(output_msg)
        sys.stdout.flush()
        
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)
    except (IndexError, ValueError) as e:
        sys.stderr.write(f"Error: Invalid file format: {e}\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
