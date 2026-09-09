# 排程示例

安排任务的资源、顺序与起止时间，表达紧前关系、准备时间和资源容量。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd aircraft_landing_problem
python -m jupyterlab aircraft_landing_problem.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [飞机降落问题](aircraft_landing_problem/aircraft_landing_problem.ipynb)：安排飞机降落顺序与时刻，考虑间隔和偏好时间。
- [批调度问题](batch_scheduling_problem/batch_scheduling_problem.ipynb)：将兼容任务组成批次，并安排批次的处理区间。
- [汽车排序问题](car_sequencing_problem/car_sequencing_problem.ipynb)：安排车辆生产顺序，最小化滑动窗口中的产能违规次数。
- [带颜色约束的车辆排序问题](car_sequencing_problem_with_colors/car_sequencing_problem_with_colors.ipynb)：安排车辆生产与颜色批次，按优先级优化多个目标。
- [柔性作业车间调度问题 (FJSP)](flexible_job_shop_problem_fjsp/flexible_job_shop_problem_fjsp.ipynb)：同时选择工序的机器分配与加工顺序。
- [带机器切换时间的柔性作业车间调度问题](flexible_job_shop_problem_with_machine_changeover_times/flexible_job_shop_problem_with_machine_changeover_times.ipynb)：在柔性车间中考虑相邻工序切换机器所需的时间。
- [带准备时间的柔性作业车间调度问题 (FJSP-SDST)](flexible_job_shop_problem_with_setup_times_fjsp_sdst/flexible_job_shop_problem_with_setup_times_fjsp_sdst.ipynb)：在柔性车间中考虑加工顺序决定的准备时间。
- [柔性资源约束项目调度问题](flexible_resource_constrained_project_scheduling_problem/flexible_resource_constrained_project_scheduling_problem.ipynb)：为任务选择兼容资源，并满足各时段的资源容量。
- [带状态约束的柔性资源受限项目调度问题 (FRCPSPS)](flexible_resource_constrained_project_scheduling_problem_with_states_frcpsps/flexible_resource_constrained_project_scheduling_problem_with_states_frcpsps.ipynb)：为任务分配资源，同时处理容量和状态兼容性约束。
- [流水车间调度问题](flow_shop_problem/flow_shop_problem.ipynb)：使用统一的作业顺序，递归计算多台机器上的完工时间。
- [作业车间调度问题 (JSSP)](job_shop_scheduling_problem_jssp/job_shop_scheduling_problem_jssp.ipynb)：结合区间和列表变量，安排工序时间与机器加工顺序。
- [带强度参数的作业车间调度问题](job_shop_scheduling_problem_with_intensity/job_shop_scheduling_problem_with_intensity.ipynb)：根据机器随时间变化的加工强度约束工序持续时间。
- [电影拍摄调度问题](movie_shoot_scheduling_problem/movie_shoot_scheduling_problem.ipynb)：安排场景拍摄顺序，通过外部函数计算演员与地点成本。
- [多模式资源受限项目调度问题 (MRCPSP)](multi_mode_resource_constrained_project_scheduling_mrcpsp/multi_mode_resource_constrained_project_scheduling_mrcpsp.ipynb)：用可选区间表示任务模式，在资源限制下选择并调度任务。
- [开放车间调度问题 (OSSP)](open_shop_scheduling_problem_ossp/open_shop_scheduling_problem_ossp.ipynb)：同时安排作业与机器上的活动顺序，避免资源重叠。
- [烤箱调度问题 (OSP)](oven_scheduling_problem_osp/oven_scheduling_problem_osp.ipynb)：组合烤箱批次并安排加工时间，考虑容量、准备和可用时段。
- [并行机调度问题 (PMS)](parallel_machine_scheduling_problem_pms/parallel_machine_scheduling_problem_pms.ipynb)：将任务分配给并行机器，优化整体完工时间。
- [可抢占资源约束项目调度问题 (PRCPSP)](preemptive_resource_constrained_project_scheduling_problem_prcpsp/preemptive_resource_constrained_project_scheduling_problem_prcpsp.ipynb)：将任务拆分为有限个子任务，在资源约束下安排执行区间。
- [带资源生产与消耗的项目调度问题](project_scheduling_with_production_and_consumption_of_resources/project_scheduling_with_production_and_consumption_of_resources.ipynb)：联合处理任务的可再生资源需求与资源库存变化。
- [资源可用性成本问题 (RACP)](resource_availability_cost_problem_racp/resource_availability_cost_problem_racp.ipynb)：在截止时间限制下决定资源容量并安排任务。
- [资源约束并行机调度问题](resource_constrained_parallel_machine_scheduling_problem/resource_constrained_parallel_machine_scheduling_problem.ipynb)：安排并行机器上的任务，同时满足共享资源容量。
- [资源约束项目调度问题 (RCPSP)](resource_constrained_project_scheduling_problem_rcpsp/resource_constrained_project_scheduling_problem_rcpsp.ipynb)：安排具有紧前关系的任务，满足各时段的资源限制。
- [简单装配线平衡问题 (SALBP)](simple_assembly_line_balancing_problem_salbp/simple_assembly_line_balancing_problem_salbp.ipynb)：将任务分配给装配工作站，满足节拍与紧前关系。
- [社交高尔夫问题](social_golfer_problem/social_golfer_problem.ipynb)：安排每周球员分组，控制不同球员重复相遇。
- [随机作业车间调度问题](stochastic_job_shop_scheduling_problem/stochastic_job_shop_scheduling_problem.ipynb)：在多个加工时间场景下安排作业和机器顺序。
- [手术调度问题](surgery_scheduling_problem/surgery_scheduling_problem.ipynb)：联合安排手术室、护士和手术时间，避免资源冲突。
- [劳动力调度问题](workforce_scheduling_problem/workforce_scheduling_problem.ipynb)：用布尔变量描述员工任务安排，优化需求覆盖。
- [劳动力轮班调度问题](workforce_shift_scheduling_problem/workforce_shift_scheduling_problem.ipynb)：分配员工班次，并对各时段的覆盖情况建模。
