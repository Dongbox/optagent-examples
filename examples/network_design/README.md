# 网络设计示例

在离散候选布局中选择设施，并考虑节点之间的相互影响。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd wind_farm_layout_optimization_problem_wflop
python -m jupyterlab wind_farm_layout_optimization_problem_wflop.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [风电场布局优化问题 (WFLOP)](wind_farm_layout_optimization_problem_wflop/wind_farm_layout_optimization_problem_wflop.ipynb)：选择风机位置，在布局约束下考虑尾流影响与发电收益。
