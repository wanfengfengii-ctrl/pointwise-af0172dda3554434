# 恒桥铸件试验室三轴振动复检归档

台架操作员登记训练和复检读数，分析员冻结训练拟合，质控员核对一个单轴采集设置能否满足两个工况。晚班按已发布标识读回当时的来源和结论。更正由操作者显式登记为新修订，可与原版本并列使用。

## 运行

在项目根目录使用 Python 3.11。工程只依赖标准库。

```sh
python3.11 -B -m demo init archive.sqlite3
python3.11 -B -m demo demo
python3.11 -B -m unittest discover -s tests -t . -v
```

初始化可以重复执行并保留合法登记和已发布的记录。演示在独立临时归档中登记样例，用手算预期核对真实结果，并演示发布异常后的回滚和更正后的固定读回。

## Python 接口

```python
from contextlib import closing

from audit.decision import report
from measure.revisions import register_batch
from publish.store import initialize_archive, open_archive
from review.handoff import read_result
from train.freeze import fit

with closing(open_archive('archive.sqlite3')) as archive:
    initialize_archive(archive)
    axes = ('X', 'Y', 'Z')
    train_rev = register_batch(archive, '训练', 'mm/s', axes,
                               [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)])
    left = register_batch(archive, '工况甲', 'mm/s', axes, [(1, 0, 0)])
    right = register_batch(archive, '工况乙', 'mm/s', axes, [(0, 1, 0)])
    fit_id = fit(archive, train_rev, '1/2')
    report_id, passed = report(archive, fit_id, left, right, '1/2', '1/2')
    result = read_result(archive, 'report', report_id)
```

登记接受批次名、单位、具名轴列和有序非空行。列必须各含一次大写 X、Y、Z，读回按 X、Y、Z 排列，原行序保留。读数、特征值声明和门槛接受 `int`、`Fraction`、整数文本、分数文本及有限小数文本。浮点对象和布尔值属于非法输入。用 `parent_rev` 指定更正来源，用 `measure.catalog.load_revision(archive, rev)` 按原标识读取来源。该函数返回批次名、单位、父标识及有理行。操作 API 使用由 `open_archive` 创建并已初始化的连接，各写操作管理自己的事务。

训练中心是逐轴均值。散布是中心化行的外积均值，分母为训练行数。调用方声明有理最高特征值，系统精确核对，并只接受一维或二维最高空间。拟合视图的 `basis` 逐项为三轴列向量，所有列共同张成允许空间，允许列基非正交。

报告的两个位置各指定一个修订和一个非负门槛。同一修订可重复使用。工况与训练单位必须一致。每个工况的分数是其各行减去训练中心后，沿同一候选实单位方向投影并平方，再按该工况行数取均值。方向正负表示同一投影。门槛使用测量单位的平方，等号达标。真和假的有效请求都获报告标识。拟合与报告发布时固定原父链，视图中的有理量使用 `分子/正分母` 字符串。

登记校验、拟合校验和报告绑定错误分别通过 `BatchInputError`、`FitInputError` 和 `CoverageInputError` 返回，且拒绝当次写入。测量写入错误为 `BatchWriteError`，成果发布错误为 `PublicationError`。拟合和报告可选的 `before_commit` 无参回调可观察暂存状态或抛出异常以检验回滚，回调须把事务控制留给发布接口。`read_result` 接受 `fit` 与 `report` 两种类型，未知标识或类型错配触发 `ResultReadError`。
