Dim oShell
Set oShell = CreateObject("WScript.Shell")
oShell.CurrentDirectory = "D:\sistema de af\sistema_activos"
oShell.Run "C:\Users\marco.heredia\AppData\Local\Programs\Python\Python312\python.exe -X utf8 run.py", 0, False
Set oShell = Nothing
