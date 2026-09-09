# 装箱示例

选择与分配物品，处理容量、相容性和多层资源限制。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd bin_packing_problem_bpp
python -m jupyterlab bin_packing_problem_bpp.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [装箱问题(BPP)](bin_packing_problem_bpp/bin_packing_problem_bpp.ipynb)：将物品划分到容量有限的箱子，最小化使用的箱子数量。
- [带冲突的装箱问题(BPPC)](bin_packing_problem_with_conflicts_bppc/bin_packing_problem_with_conflicts_bppc.ipynb)：在箱子容量约束之外，禁止相互冲突的物品装入同一箱。
- [彩色装箱问题 (CBPP)](colored_bin_packing_problem_cbpp/colored_bin_packing_problem_cbpp.ipynb)：让同箱物品具有不同颜色，并满足容量限制。
- [带约束的露天矿坑极限问题 (CPIT)](constrained_pit_limit_problem_cpit/constrained_pit_limit_problem_cpit.ipynb)：安排矿块的开采时段，满足前置关系和资源约束。
- [切割下料问题](cutting_stock_problem/cutting_stock_problem.ipynb)：用两层集合描述物品、条带与卷材的分配关系。
- [团体座位预订背包问题 (GSR-KP)](group_seat_reservation_knapsack_problem_gsr_kp/group_seat_reservation_knapsack_problem_gsr_kp.ipynb)：选择团体预订，并用可选区间分配连续座位。
- [背包问题](knapsack_problem/knapsack_problem.ipynb)：选择总重量不超过容量的物品，使总价值最大。
- [货架装箱问题](shelf_packing_problem/shelf_packing_problem.ipynb)：同时考虑箱子和货架的容量，按优先级减少货架与箱子数量。
- [钢厂板坯设计问题](steel_mill_slab_design_problem/steel_mill_slab_design_problem.ipynb)：把订单分配给板坯，考虑容量与颜色限制并减少损耗。
- [随机装箱问题](stochastic_packing_problem/stochastic_packing_problem.ipynb)：在物品重量具有不确定性的条件下安排装箱。
- [玩具示例](toy/toy.ipynb)：从一个小型物品选择模型开始，理解变量、约束和目标。
- [卡车装载问题](truck_loading_problem/truck_loading_problem.ipynb)：将物品分配给卡车，在装载约束下优化配送方案。
