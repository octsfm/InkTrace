/**
 * Python后端进程管理器
 * 
 * 作者：孔利群
 */

const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');
const os = require('os');

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

        await this._freePort(port);
        const stillInUse = await this._isPortInUse(port);
        if (stillInUse) {
            throw new Error(`端口 ${port} 被占用，请先结束冲突进程后重试`);
        }

        this.port = port;
        this.status = 'starting';
        this._notifyStatusChange();

        console.log(`Starting backend: ${backendPath}, isDev: ${isDev}`);

        return new Promise((resolve, reject) => {
            const backendDir = path.dirname(backendPath);
            const userDataDir = path.join(process.env.APPDATA || path.join(os.homedir(), '.inktrace'), 'InkTrace');
            const dbPath = path.join(userDataDir, 'inktrace.db');
            const chromaDir = path.join(userDataDir, 'chroma');
            fs.mkdirSync(userDataDir, { recursive: true });
            fs.mkdirSync(chromaDir, { recursive: true });
            
            const env = {
                ...process.env,
                PYTHONUTF8: '1',
                PYTHONIOENCODING: 'utf-8',
                PORT: String(port),
                INKTRACE_PORT: String(port),
                INKTRACE_HOST: '127.0.0.1',
                INKTRACE_DEBUG: isDev ? 'true' : 'false',
                INKTRACE_DB_PATH: dbPath,
                INKTRACE_CHROMA_DIR: chromaDir
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
                console.log(`[Backend] ${data.toString('utf8')}`);
            });

            this.process.stderr.on('data', (data) => {
                console.error(`[Backend Error] ${data.toString('utf8')}`);
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

            this._waitForBackend(port, 45000)
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
                if (!this.process) {
                    reject(new Error('Backend process exited unexpectedly'));
                    return;
                }
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

    _freePort(port) {
        if (process.platform !== 'win32') {
            return Promise.resolve();
        }
        return new Promise((resolve) => {
            const cmd = `for /f "tokens=5" %a in ('netstat -ano ^| findstr LISTENING ^| findstr :${port}') do @echo %a`;
            const killer = spawn('cmd.exe', ['/c', cmd], { stdio: ['ignore', 'pipe', 'ignore'] });
            let output = '';
            killer.stdout.on('data', (data) => {
                output += data.toString();
            });
            killer.on('close', () => {
                const pids = Array.from(
                    new Set(
                        output
                            .split(/\r?\n/)
                            .map((line) => line.trim())
                            .filter((line) => /^\d+$/.test(line))
                    )
                );
                if (pids.length === 0) {
                    return resolve();
                }
                let done = 0;
                pids.forEach((pid) => {
                    if (Number(pid) <= 4) {
                        done += 1;
                        if (done >= pids.length) resolve();
                        return;
                    }
                    const tk = spawn('taskkill', ['/PID', String(pid), '/F'], { stdio: 'ignore' });
                    tk.on('close', () => {
                        done += 1;
                        if (done >= pids.length) resolve();
                    });
                });
            });
        });
    }

    _isPortInUse(port) {
        return new Promise((resolve) => {
            const req = http.request({
                hostname: '127.0.0.1',
                port: port,
                path: '/health',
                method: 'GET',
                timeout: 800
            }, () => resolve(true));
            req.on('error', () => resolve(false));
            req.on('timeout', () => {
                req.destroy();
                resolve(false);
            });
            req.end();
        });
    }
}

module.exports = { ProcessManager };
