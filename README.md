# 洁净室与手术室环境联控 Python

这是一个可运行的洁净室与手术室环境联控服务。当前基线提供领域资产、测点历史、幂等动作、版本配置和持久化任务，并保留 12 条可由测试观察的有限业务链。

这些链路用于证明 Feature 题的现状入口真实存在；它们只实现当前明确的基础行为，复杂协调、融合、仲裁、恢复与迁移仍留给后续开发。

```powershell
python -m cleanroom --demo
python -m unittest discover -s tests -v
```
