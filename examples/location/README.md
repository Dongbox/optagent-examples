# 选址示例

选择设施位置、分配客户或划分数据，权衡距离与成本。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd capacitated_facility_location_problem_cflp
python -m jupyterlab capacitated_facility_location_problem_cflp.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [容量约束设施选址问题(CFLP)](capacitated_facility_location_problem_cflp/capacitated_facility_location_problem_cflp.ipynb)：在设施容量限制下分配客户，权衡设施开放成本与服务成本。
- [设施选址问题 (FLP)](facility_location_problem_flp/facility_location_problem_flp.ipynb)：选择开放的设施及客户分配方案，最小化总成本。
- [K-Means 聚类问题 (MSSC)](k_means_clustering_problem_mssc/k_means_clustering_problem_mssc.ipynb)：用集合变量划分观测点，最小化各簇内的平方距离之和。
- [最大割问题](max_cut_problem/max_cut_problem.ipynb)：把图的顶点划分为两组，最大化跨组边的总权重。
- [二次分配问题 (QAP)](quadratic_assignment_problem_qap/quadratic_assignment_problem_qap.ipynb)：将设施分配到位置，最小化流量与距离共同决定的成本。
- [最小圆问题](smallest_circle_problem/smallest_circle_problem.ipynb)：选择圆心，使覆盖所有给定点的圆的半径最小。
