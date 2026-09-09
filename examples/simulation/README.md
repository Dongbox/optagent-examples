# 仿真优化示例

学习外部函数建模，并对照直接表达工程公式的实现。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd cantilevered_beam_problem
python -m jupyterlab cantilevered_beam_problem.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [悬臂梁问题](cantilevered_beam_problem/cantilevered_beam_problem.ipynb)：选择梁的连续与离散尺寸，在应力和挠度约束下最小化体积。
- [Hosaki函数](hosaki_function/hosaki_function.ipynb)：将 Hosaki 函数作为 Python 外部回调接入优化模型。
- [收益管理问题](revenue_management_problem/revenue_management_problem.ipynb)：用仿真评价采购和预留决策，优化平均净收益。
