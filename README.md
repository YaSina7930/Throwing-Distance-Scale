# 投掷距离标尺

《三角洲行动》投掷物俯仰标尺叠层。平视 0°，抬头为正、低头为负。支持右手远投、左手低抛、威龙 C4、威龙大招、红狼手炮。

## 安装

从 [Releases](https://github.com/YaSina7930/Throwing-Distance-Scale/releases) 下载 `ThrowingDistanceScale-windows-x64.zip`，解压后运行 `ThrowingDistanceScale.exe`。

游戏必须使用 **无边框窗口**。独占全屏叠不上。

## 从源码运行

```powershell
python -m pip install -r requirements.txt
python run.py
```

需要 Python 3.11+。

## 使用

- **F5** 平视对准 0°（热键可改）
- **F6** 抬头最高对准 +80°（热键可改）
- 「浮标跟随」数字越大针走得越慢
- 两个标尺 A/B 可同时显示，各自选预设、位置、高度、镜像
- 信息框单独开关，可显示 A/B 读数
- 右手远投：秒数 = 爆炸剩余时间 + 0.2 秒出手
- 威龙大招 / 红狼手炮：固定 3 秒引信。青色「瞬」2.0–2.5 秒，红色「瞬」2.5–3.0 秒落地瞬爆

设置写在解压目录 `data/config.json`。

右手远投适用角色：蛊，牧羊人，乌鲁鲁，液氮，露娜。左手低抛适用角色：红狼，风衣，旅人。「爆」表示瞬爆。

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File build_release.ps1
```
