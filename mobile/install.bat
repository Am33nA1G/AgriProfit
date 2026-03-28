@echo off
echo Starting npm install... > install_log.txt
echo Timestamp: %date% %time% >> install_log.txt
npm install react-native-toast-message lucide-react-native expo-haptics --legacy-peer-deps >> install_log.txt 2>&1
echo Exit code: %errorlevel% >> install_log.txt
echo DONE >> install_log.txt
