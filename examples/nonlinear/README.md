# 非线性优化示例

使用连续变量和非线性表达式描述拟合、混合、几何与资源分配。

## 安装与运行

先按 [OptAgent 安装指南](https://optagent.pages.dev/start/installation/) 安装 OptAgent 并配置许可证。在本目录安装工具与依赖：

```bash
python -m pip install -r ../../requirements-dev.txt
```

进入要运行的案例目录，从该目录启动 JupyterLab。例如：

```bash
cd advertising_campaign_problem
python -m jupyterlab advertising_campaign_problem.ipynb
```

保持 Notebook 与实例目录的相对位置。按顺序执行单元；实例路径和求解预算见各 Notebook。

## 案例

- [广告投放问题](advertising_campaign_problem/advertising_campaign_problem.ipynb)：分配广告投放资源，用非线性表达式描述投放效果。
- [Branin 函数](branin_function/branin_function.ipynb)：用两个浮点变量构造 Branin 函数并求最小值。
- [曲线拟合问题](curve_fitting_problem/curve_fitting_problem.ipynb)：拟合非线性函数的参数，最小化预测值与观测值的平方误差。
- [最优水桶问题](optimal_bucket_problem/optimal_bucket_problem.ipynb)：在材料面积限制下选择水桶尺寸，最大化容积。
- [混流问题](pooling_problem/pooling_problem.ipynb)：安排原料流向与混合比例，在质量约束下优化混流网络。
- [投资组合选择优化问题](portfolio_selection_optimization_problem/portfolio_selection_optimization_problem.ipynb)：分配投资比例，在收益要求下优化由协方差描述的风险。
