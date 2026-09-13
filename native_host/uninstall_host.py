import winreg
NAME='com.azzlaer.videomkvhost';key=rf'Software\Google\Chrome\NativeMessagingHosts\{NAME}'
try:winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key);print('Native Host eliminado.')
except FileNotFoundError:print('No estaba registrado.')
