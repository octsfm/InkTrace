/**
 * Python后端进程管理器
 * 
 * 作者：孔利群
 */

const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

class ProcessManager {
    constructor() {
        this.process = null;
        this.port = null;
        this.status = 'stopped';
        this.statusListeners = [];
    }

    async start(backendPath, port, isDev = true) {
        if (this.process) {
            await this.stop();
        }

        this.port = port;
        this.status = 'starting';
        this._notifyStatusChange();

        console.log(`Starting backend: ${backendPath}, isDev: ${isDev}`);

        return new Promise((resolve, reject) => {
            const backendDir = path.dirname(backendPath);
            
            const env = {
                ...process.env,
                PYTHONIOENCODING: 'utf-8',
                PORT: String(port)
            };

            let command, args;
            if (isDev) {
                command = this._getPythonPath();
                args = [backendPath];
            } else {
                command = backendPath;
                args = [];
            }

            console.log(`Command: ${command}, Args: ${args.join(' ')}`);

            this.process = spawn(command, args, {
                cwd: backendDir,
                env: env,
                stdio: ['ignore', 'pipe', 'pipe']
            });

            this.process.stdout.on('data', (data) => {
                console.log(`[Backend] ${data.toString()}`);
            });

            this.process.stderr.on('data', (data) => {
                console.error(`[Backend Error] ${data.toString()}`);
            });

            this.process.on('error', (error) => {
                console.error('Failed to start backend:', error);
                this.status = 'error';
                this._notifyStatusChange();
                reject(error);
            });

            this.process.on('exit', (code) => {
                console.log(`Backend exited with code ${code}`);
                this.process = null;
                this.status = 'stopped';
                this._notifyStatusChange();
            });

            this._waitForBackend(port, 30000)
                .then(() => {
                    this.status = 'running';
                    this._notifyStatusChange();
                    resolve();
                })
                .catch((error) => {
                    this.status = 'error';
                    this._notifyStatusChange();
                    reject(error);
                });
        });
    }

    async stop() {
        if (!this.process) {
            return;
        }

        return new Promise((resolve) => {
            this.status = 'stopping';
            this._notifyStatusChange();

            const timeout = setTimeout(() => {
                if (this.process) {
                    this.process.kill('SIGKILL');
                }
            }, 5000);

            this.process.on('exit', () => {
                clearTimeout(timeout);
                this.process = null;
                this.status = 'stopped';
                this._notifyStatusChange();
                resolve();
            });

            this.process.kill('SIGTERM');
        });
    }

    async restart() {
        const backendPath = this.process 
            ? this.process.spawnargs[1] 
            : null;
        
        if (backendPath) {
            await this.stop();
            await this.start(backendPath, this.port);
        }
    }

    getStatus() {
        return {
            status: this.status,
            port: this.port,
            pid: this.process ? this.process.pid : null
        };
    }

    onStatusChange(callback) {
        this.statusListeners.push(callback);
    }

    _notifyStatusChange() {
        const status = this.getStatus();
        this.statusListeners.forEach(callback => callback(status));
    }

    _getPythonPath() {
        const isWindows = process.platform === 'win32';
        
        if (process.resourcesPath) {
            const pythonExe = isWindows ? 'python.exe' : 'python3';
            const bundledPython = path.join(process.resourcesPath, 'python', pythonExe);
            if (fs.existsSync(bundledPython)) {
                return bundledPython;
            }
        }
        
        return isWindows ? 'python' : 'python3';
    }

    _waitForBackend(port, timeout) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();
            
            const checkServer = () => {
                const req = http.request({
                    hostname: 'localhost',
                    port: port,
                    path: '/health',
                    method: 'GET',
                    timeout: 1000
                }, (res) => {
                    if (res.statusCode === 200) {
                        resolve();
                    } else {
                        retry();
                    }
                });

                req.on('error', () => {
                    retry();
                });

                req.on('timeout', () => {
                    req.destroy();
                    retry();
                });

                req.end();
            };

            const retry = () => {
                if (Date.now() - startTime > timeout) {
                    reject(new Error('Backend startup timeout'));
                } else {
                    setTimeout(checkServer, 500);
                }
            };

            checkServer();
        });
    }
}

module.exports = { ProcessManager };
