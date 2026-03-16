/**
 * 桌面应用诊断脚本
 * 作者：孔利群
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('=== InkTrace 桌面应用诊断 ===');

// 检查关键文件
const filesToCheck = [
    'dist/win-unpacked/InkTrace.exe',
    'dist/win-unpacked/resources/backend/inktrace-backend.exe',
    'dist/win-unpacked/resources/app.asar',
    'desktop/main.js',
    'desktop/process-manager.js'
];

filesToCheck.forEach(file => {
    const fullPath = path.join(__dirname, file);
    const exists = fs.existsSync(fullPath);
    console.log(`${exists ? '✅' : '❌'} ${file}: ${exists ? '存在' : '缺失'}`);
});

// 检查后端exe是否可执行
const backendExe = path.join(__dirname, 'dist/win-unpacked/resources/backend/inktrace-backend.exe');
if (fs.existsSync(backendExe)) {
    console.log('\n=== 测试后端启动 ===');
    
    const backendProcess = spawn(backendExe, [], {
        cwd: path.dirname(backendExe),
        stdio: ['ignore', 'pipe', 'pipe']
    });
    
    backendProcess.stdout.on('data', (data) => {
        console.log(`[Backend] ${data.toString()}`);
    });
    
    backendProcess.stderr.on('data', (data) => {
        console.error(`[Backend Error] ${data.toString()}`);
    });
    
    backendProcess.on('error', (error) => {
        console.error('后端启动失败:', error);
    });
    
    // 5秒后停止测试
    setTimeout(() => {
        backendProcess.kill();
        console.log('后端测试完成');
    }, 5000);
}

console.log('\n=== 诊断完成 ===');