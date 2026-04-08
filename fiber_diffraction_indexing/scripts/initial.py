#1.初始化软件：initialize.py
    #1.1 读取input文件，确定每代种群大小等参数
    #1.2 生成种群数量的随机晶胞
    #1.3 导出文件：cell_0.txt

#import numpy as np
import os
import random
import math
import time
import argparse
import sys

#1.1 读取input文件，确定每代种群大小,是否给出c轴长度，存活数量
def read_input():
    #读取input文件，通过-i或者--input指定
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='input file')
    args = parser.parse_args()
    filename = args.input
    input_file = open(filename,'r')
    input_lines = input_file.readlines()
    input_file.close()

    #确定每代种群大小
    population_size = int(input_lines[3].split()[0])#种群大小,第四行
    # 是否给出c轴长度
    c_axis = float(input_lines[10].split()[0])#是否给出c轴长度，第11行,c_axis=0,不给出，其他为固定c之后的c轴长度
    #存活数量
    survive = int(input_lines[4].split()[0])#存活数量，第五行
    try:
        all_min=input_lines[24].strip(' ' and '\n').split()
        all_max=input_lines[25].strip(' ' and '\n').split()
        tilt_stat=int(input_lines[26])
    except:
        sys.stdout.write("FORMAT of max and min value is wrong!please check!")
        exit()
    return population_size,c_axis,survive,all_min,all_max,tilt_stat

#1.2 生成种群数量的随机晶胞
def generate_cell(population_size,c_axis,all_min,all_max,tilt_stat):
    #生成种群数量的随机晶胞
    cell = []
    tilt_angle=[]

    for i in range(population_size):
        #随机生成晶胞参数
        a = random.uniform(float(all_min[0]),float(all_max[0]))#(5.0, 15.0)
        b = random.uniform(float(all_min[1]),float(all_max[1]))
        #a必须大于b

        if a < b:
            a, b = b, a
        if c_axis == 0:
            c = random.uniform(float(all_min[2]),float(all_max[2]))
        else:
            c = c_axis

        alpha = random.uniform(float(all_min[3]),float(all_max[3]))
        beta = random.uniform(float(all_min[4]),float(all_max[4]))
        gamma = random.uniform(float(all_min[5]),float(all_max[5]))
        if (tilt_stat == 1):
            tilt_angle.append(random.uniform(-10,10))
        else:
            tilt_angle.append(0.0)
        #生成晶胞矩阵
        cell_matrix = [a,b,c,alpha,beta,gamma]
        cell.append(cell_matrix)
    return cell,tilt_angle

#1.3 导出文件：cell_0.txt
def export_cell(cell):
    #导出文件：cell_0.txt
    cell_file = open(os.path.join(os.getcwd(), 'cell_0.txt'), 'w')
    for i in range(len(cell)):
        #保留两位小数，以一行输出，分别是a，b，c，alpha，beta，gamma
        cell_file.write('%.4f'%cell[i][0]+' '+'%.4f'%cell[i][1]+' '+'%.4f'%cell[i][2]+' '+'%.4f'%cell[i][3]+' '+'%.4f'%cell[i][4]+' '+'%.4f'%cell[i][5]+'\n')
    cell_file.close()

def export_cell_tilt(cell,tilt_angle):
    #导出文件：cell_0.txt
    cell_file = open(os.path.join(os.getcwd(), 'cell_0.txt'), 'w')
    for i in range(len(cell)):
        #保留两位小数，以一行输出，分别是a，b，c，alpha，beta，gamma
        cell_file.write('%.4f'%cell[i][0]+' '+'%.4f'%cell[i][1]+' '+'%.4f'%cell[i][2]+' '+'%.4f'%cell[i][3]+' '+'%.4f'%cell[i][4]+' '+'%.4f'%cell[i][5]+' '+'%.4f'%tilt_angle[i]+'\n')
    cell_file.close()

#主程序
if __name__ == '__main__':
    #1.1 读取input文件，确定每代种群大小,是否给出c轴长度，存活数量
    population_size,c_axis,survive,all_min,all_max,tilt_stat=read_input()
    #1.2 生成种群数量的随机晶胞
    cell,tilt_angle=generate_cell(population_size,c_axis,all_min,all_max,tilt_stat)#,a_min,b_min,c_min,alpha_min,beta_min,gamma_min,a_max,b_max,c_max,alpha_max,beta_max,gamma_max)
    #1.3 导出文件：cell_0.txt
    if tilt_stat == 1:
        export_cell_tilt(cell,tilt_angle)
    else:    
        export_cell(cell)


