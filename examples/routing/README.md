# 路径优化示例

安排车辆或人员的访问顺序，处理容量、时间窗、取送货与多时段配送。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd capacitated_arc_routing_problem_carp
python -m jupyterlab capacitated_arc_routing_problem_carp.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [容量约束弧路径问题(CARP)](capacitated_arc_routing_problem_carp/capacitated_arc_routing_problem_carp.ipynb)：为需要服务的道路安排车辆与访问顺序，满足载荷限制。
- [容量约束车辆路径问题(CVRP)](capacitated_vehicle_routing_problem_cvrp/capacitated_vehicle_routing_problem_cvrp.ipynb)：用列表变量表示车辆路线，兼顾车辆数与行驶距离。
- [带时间窗与固定休息的容量约束车辆路径问题](capacitated_vehicle_routing_problem_with_time_windows_and_regular_breaks/capacitated_vehicle_routing_problem_with_time_windows_and_regular_breaks.ipynb)：在客户时间窗和车辆容量之外，安排行程中的固定休息。
- [集群车辆路径问题 (cluVRP)](clustered_vehicle_routing_cluvrp/clustered_vehicle_routing_cluvrp.ipynb)：同时安排客户集群的访问顺序和集群内部的路线。
- [电话叫车问题 (DARP)](dial_a_ride_problem_darp/dial_a_ride_problem_darp.ipynb)：安排成对的接送请求，考虑时间窗与乘车时间限制。
- [库存路径问题 (IRP)](inventory_routing_problem_irp/inventory_routing_problem_irp.ipynb)：联合安排多时段补货量、库存与配送路线。
- [选址路径问题 (LRP)](location_routing_problem_lrp/location_routing_problem_lrp.ipynb)：联合决定配送中心的开放、客户分配与车辆路线。
- [多仓库车辆路径问题 (MDVRP)](multi_depot_vehicle_routing_problem_mdvrp/multi_depot_vehicle_routing_problem_mdvrp.ipynb)：为多个仓库的车辆分配客户并安排访问顺序。
- [多趟容量受限车辆路径问题 (MTCVRP)](multi_trip_capacitated_vehicle_routing_problem_mtcvrp/multi_trip_capacitated_vehicle_routing_problem_mtcvrp.ipynb)：允许车辆返回仓库后继续配送，递归计算沿途载荷。
- [订单分批问题](order_batching_problem/order_batching_problem.ipynb)：将订单划分为批次，在拣货容量限制下考虑通道访问成本。
- [订单拣选问题](order_picking_problem/order_picking_problem.ipynb)：安排仓库中的订单拣选顺序，减少行驶距离。
- [带时间窗的取送货问题 (PDPTW)](pickup_and_delivery_problem_with_time_windows_pdptw/pickup_and_delivery_problem_with_time_windows_pdptw.ipynb)：让成对取送请求由同一车辆服务，满足顺序、载荷和时间要求。
- [带收益收集的车辆路径问题 (PCVRP)](prize_collecting_vehicle_routing_problem_pcvrp/prize_collecting_vehicle_routing_problem_pcvrp.ipynb)：选择值得服务的客户，权衡收集的收益与路线成本。
- [拆分配送车辆路径问题 (SDVRP)](split_delivery_vehicle_routing_problem_sdvrp/split_delivery_vehicle_routing_problem_sdvrp.ipynb)：允许多个车辆共同满足同一客户的配送需求。
- [时间相关带时间窗车辆路径问题 (TDCVRPTW)](time_dependent_routing_problem_with_time_windows_tdcvrptw/time_dependent_routing_problem_with_time_windows_tdcvrptw.ipynb)：在行驶时间随出发时刻变化的条件下安排配送路线。
- [旅行商问题 (TSP)](traveling_salesman_problem_tsp/traveling_salesman_problem_tsp.ipynb)：用一个列表表示城市访问顺序，最小化闭环总距离。
- [带吃水限制的旅行商问题 (TSPDL)](traveling_salesman_problem_with_draft_limits_tspdl/traveling_salesman_problem_with_draft_limits_tspdl.ipynb)：安排港口访问顺序，并满足载荷变化带来的吃水限制。
- [带回程取货的车辆路径问题 (VRPB)](vehicle_routing_problem_with_backhauls_vrpb/vehicle_routing_problem_with_backhauls_vrpb.ipynb)：联合安排配送与回程取货，约束不同客户类型的访问顺序。
- [带时间窗的车辆路径问题 (CVRPTW)](vehicle_routing_problem_with_time_windows_cvrptw/vehicle_routing_problem_with_time_windows_cvrptw.ipynb)：为容量有限的车辆安排路线，并计算客户访问时间。
- [带转运设施的车辆路径问题 (VRPTF)](vehicle_routing_problem_with_transshipment_facilities_vrptf/vehicle_routing_problem_with_transshipment_facilities_vrptf.ipynb)：允许直接配送或经转运设施服务客户，权衡路线与分配成本。
