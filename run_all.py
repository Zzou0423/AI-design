"""
一体化问卷生成和查看工具
生成问卷并启动 Web 服务器
"""

import os
import sys
from pathlib import Path
import json
import webbrowser
from threading import Timer
from datetime import datetime
import uvicorn
import schedule
import time
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel
from dotenv import load_dotenv
import shutil

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

# 导入服务
from app.services.survey_service import SurveyService
from app.utils.response_saver import ResponseSaver
from app.models.user import user_store
from app.utils.session_manager import session_manager
from app.utils.user_survey_manager import user_survey_manager

# 全局变量
generated_survey = None
response_saver = ResponseSaver()
surveys_storage = {}  # 存储问卷 {survey_id: survey_data}

# ==========================================
# 环境配置
# ==========================================
# 从环境变量读取配置，提供默认值
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
ALLOWED_HOSTS_STR = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(",")]

# 如果是生产环境，添加 * 到允许的源（用于CORS）
if IS_PRODUCTION:
    CORS_ORIGINS = ALLOWED_HOSTS
else:
    # 开发环境允许所有源
    CORS_ORIGINS = ["*"]

print(f"\n[配置] 运行环境: {ENVIRONMENT}")
print(f"[配置] 生产模式: {IS_PRODUCTION}")
print(f"[配置] 允许的主机: {ALLOWED_HOSTS}")
print(f"[配置] CORS源: {CORS_ORIGINS}")

# 创建 FastAPI 应用（生产环境关闭调试）
app = FastAPI(
    title="AI Survey Assistant",
    version="0.1.0",
    debug=not IS_PRODUCTION,  # 生产环境关闭 debug
    docs_url=None if IS_PRODUCTION else "/docs",  # 生产环境隐藏文档
    redoc_url=None if IS_PRODUCTION else "/redoc"
)

# 添加CORS中间件（根据环境变量配置）
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,  # 使用配置的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建静态文件目录
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/login.html", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """返回登录页面"""
    with open("static/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/workspace", response_class=HTMLResponse)
async def workspace():
    """返回工作空间页面"""
    with open("static/workspace.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/", response_class=HTMLResponse)
async def index():
    """返回主页面（需要登录）"""
    # 检查登录状态的脚本
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Survey Assistant</title>
        <link rel="stylesheet" href="/static/style.css">
        <script>
            // 检查登录状态
            const sessionId = localStorage.getItem('session_id');
            const username = localStorage.getItem('username');
            
            if (!sessionId || !username) {
                window.location.href = '/login.html';
            } else {
                // 验证会话是否仍然有效
                fetch(`/api/user/info?session_id=${sessionId}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        // 会话无效，清除本地存储并跳转到登录页
                        localStorage.removeItem('session_id');
                        localStorage.removeItem('username');
                        window.location.href = '/login.html';
                    }
                })
                .catch(error => {
                    console.error('验证会话失败:', error);
                    // 网络错误时保持当前状态，不强制跳转
                });
            }
        </script>
    </head>
    <body>
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <header class="header" style="margin: 0; white-space: nowrap;">
                    <h1 style="margin: 0; font-size: 32px;">AI Survey Assistant</h1>
                    <p style="margin: 0; font-size: 16px;">智能问卷生成与分析工具</p>
                </header>
                <div style="display: flex; gap: 8px; align-items: center; white-space: nowrap;">
                    <span id="userInfo" style="color: var(--text-secondary); font-size: 14px;"></span>
                    <button class="btn-secondary" onclick="goToWorkspace()" style="padding: 8px 12px; font-size: 14px;">工作空间</button>
                    <button class="btn-secondary" onclick="logout()" style="padding: 8px 12px; font-size: 14px;">登出</button>
                </div>
            </div>
            <main class="main-content">
                <section class="input-section">
                    <h2>生成问卷</h2>
                    <div class="input-group">
                        <label for="surveyPrompt">问卷需求描述</label>
                        <textarea id="surveyPrompt" placeholder="请输入你想要生成的问卷需求，例如：&#10;• 用户满意度调查&#10;• 产品使用体验评估&#10;• 员工工作满意度调研&#10;• 客户需求调查&#10;等等..." rows="4"></textarea>
                    </div>
                    <button id="generateBtn" class="btn-primary">生成问卷</button>
                </section>
                
                <section id="loadingSection" class="loading-section" style="display: none;">
                    <div class="loading-header">
                        <h3>✨ 智能生成中</h3>
                        <div class="loading-icon">⏳</div>
                    </div>
                    
                    <!-- 进度条 -->
                    <div class="progress-container">
                        <div class="progress-info">
                            <span id="loadingStatus" class="progress-status">准备开始</span>
                            <span id="progressPercent" class="progress-percent">0%</span>
                        </div>
                        <div class="progress-bar-wrapper">
                            <div class="progress-bar">
                                <div id="progressBarFill" class="progress-bar-fill" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- AI思考过程 -->
                    <div id="thinkingProcess" class="thinking-process">
                        <h4>🧠 AI思考过程</h4>
                        <div id="thinkingMessages" class="thinking-messages">
                            <!-- 思考消息将动态添加 -->
                        </div>
                    </div>
                    
                    <!-- 时间估算 -->
                    <p id="timeEstimate" class="time-estimate">
                        预计 15-20 秒
                    </p>
                </section>
                
                <section id="resultSection" class="result-section" style="display: none;">
                    <h2>生成的问卷</h2>
                    <div id="surveyResult"></div>
                </section>
            </main>
            
            <footer class="footer">
                <p>&copy; 2025 AI Survey Assistant</p>
            </footer>
        </div>
        
        <script src="/static/app.js"></script>
        <script>
            // 显示用户信息
            window.addEventListener('DOMContentLoaded', function() {
                const username = localStorage.getItem('username');
                if (username) {
                    document.getElementById('userInfo').textContent = '当前用户: ' + username;
                }
            });
            
            // 跳转到工作空间
            function goToWorkspace() {
                window.location.href = '/workspace';
            }
            
            // 登出
            async function logout() {
                const sessionId = localStorage.getItem('session_id');
                if (sessionId) {
                    try {
                        await fetch('/api/logout', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ session_id: sessionId })
                        });
                    } catch (e) {
                        console.error('登出失败:', e);
                    }
                }
                
                localStorage.removeItem('session_id');
                localStorage.removeItem('username');
                window.location.href = '/login.html';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/survey")
async def get_survey():
    """获取生成的问卷"""
    if generated_survey is None:
        raise HTTPException(status_code=404, detail="Survey not generated yet")
    return JSONResponse(content=generated_survey)


@app.post("/api/generate")
async def generate_survey_api(request: dict):
    """生成问卷 API（支持流式输出）"""
    global generated_survey, service
    
    if service is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    
    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    
    from fastapi.responses import StreamingResponse
    import asyncio
    
    async def generate_stream():
        try:
            # 第一步：分析需求
            yield 'data: {"type": "step", "message": "正在分析您的需求..."}\n\n'
            yield 'data: {"type": "thinking", "message": "🤔 理解用户需求，确定问卷主题和目标受众..."}\n\n'
            await asyncio.sleep(0.3)
            
            # 进行需求扩写
            try:
                yield 'data: {"type": "thinking", "message": "💡 正在优化和扩展您的需求描述..."}\n\n'
                enhanced_prompt = service.enhance_requirement(prompt)
                # 如果扩写返回空或异常，使用原始prompt
                if not enhanced_prompt or len(enhanced_prompt.strip()) < 5:
                    enhanced_prompt = prompt
                    yield 'data: {"type": "thinking", "message": "⚠️ 需求扩写遇到问题，使用原始输入继续..."}\n\n'
                else:
                    yield 'data: {"type": "thinking", "message": "✅ 需求扩写完成，已优化描述内容..."}\n\n'
            except Exception as enhance_error:
                print(f"需求扩写失败，使用原始输入: {enhance_error}")
                enhanced_prompt = prompt
                yield 'data: {"type": "thinking", "message": "⚠️ 需求扩写失败，使用原始输入继续..."}\n\n'
            
            # 第二步：优化需求描述
            yield f'data: {{"type": "step", "message": "需求优化完成"}}\n\n'
            await asyncio.sleep(0.5)
            
            # 第三步：检索相关案例
            yield 'data: {"type": "step", "message": "正在检索相关案例..."}\n\n'
            yield 'data: {"type": "thinking", "message": "🔍 从知识库中搜索相似的问卷案例..."}\n\n'
            await asyncio.sleep(0.5)
            yield 'data: {"type": "thinking", "message": "📚 分析案例结构，提取最佳实践..."}\n\n'
            await asyncio.sleep(0.3)
            
            # 第四步：生成问卷
            yield 'data: {"type": "step", "message": "正在生成问卷内容..."}\n\n'
            yield 'data: {"type": "thinking", "message": "🧠 AI开始构思问卷结构和问题设计..."}\n\n'
            await asyncio.sleep(0.3)
            
            print(f"\n[INFO] Starting survey generation, prompt: {enhanced_prompt[:100]}...")
            
            # 生成问卷（这是耗时操作，可能需要较长时间）
            # 添加重试机制
            max_retries = 3
            retry_count = 0
            generated_survey = None
            
            while retry_count < max_retries:
                try:
                    print(f"[INFO] Attempting survey generation (attempt {retry_count + 1}/{max_retries})")
                    
                    if retry_count == 0:
                        yield 'data: {"type": "thinking", "message": "🎯 确定问卷目标：明确调研目的和预期结果..."}\n\n'
                        await asyncio.sleep(0.5)
                        yield 'data: {"type": "progress", "progress": 75, "message": "正在设计问题结构..."}\n\n'
                        
                        yield 'data: {"type": "thinking", "message": "📝 设计问题类型：选择题、量表题、开放题的最佳组合..."}\n\n'
                        await asyncio.sleep(0.5)
                        yield 'data: {"type": "progress", "progress": 80, "message": "正在生成问题内容..."}\n\n'
                        
                        yield 'data: {"type": "thinking", "message": "🔗 构建逻辑关系：确保问题间的连贯性和递进性..."}\n\n'
                        await asyncio.sleep(0.5)
                        yield 'data: {"type": "progress", "progress": 85, "message": "正在优化问题表述..."}\n\n'
                        
                        yield 'data: {"type": "thinking", "message": "✨ 优化问题表述：确保语言清晰、易懂、无歧义..."}\n\n'
                        await asyncio.sleep(0.5)
                        yield 'data: {"type": "progress", "progress": 90, "message": "正在完善问卷结构..."}\n\n'
                        
                        yield 'data: {"type": "thinking", "message": "🎨 完善问卷结构：添加标题、说明和感谢语..."}\n\n'
                        await asyncio.sleep(0.5)
                        yield 'data: {"type": "progress", "progress": 95, "message": "正在生成最终问卷..."}\n\n'
                    
                    generated_survey = service.create_survey(enhanced_prompt)
                    print(f"[INFO] Survey generation successful: {generated_survey is not None}")
                    
                    if generated_survey:
                        yield 'data: {"type": "thinking", "message": "🎉 问卷生成完成！正在验证和优化..."}\n\n'
                        await asyncio.sleep(0.3)
                        yield 'data: {"type": "progress", "progress": 98, "message": "正在验证问卷内容..."}\n\n'
                    
                    break  # 成功则跳出循环
                except Exception as retry_error:
                    retry_count += 1
                    error_msg = str(retry_error)
                    print(f"[ERROR] Survey generation failed (attempt {retry_count}): {error_msg}")
                    if "Connection" in error_msg or "10054" in error_msg:
                        print(f"\n[WARN] Network error, retrying {retry_count}/{max_retries}...")
                        yield f'data: {{"type": "step", "message": "网络连接失败，正在重试 ({retry_count}/{max_retries})..."}}\n\n'
                        await asyncio.sleep(2)  # 等待2秒后重试
                    else:
                        # 其他错误不需要重试，直接抛出
                        raise
            
            # 如果重试后还是失败
            if not generated_survey:
                raise Exception("网络连接不稳定，已重试3次仍然失败，请稍后再试")
            
            print(f"\n[OK] Survey generated successfully, {len(generated_survey.get('questions', []))} questions")
            
            # 验证生成的问卷是否有效
            if not generated_survey:
                raise ValueError("生成的问卷为空")
            if not generated_survey.get('questions'):
                raise ValueError("生成的问卷没有包含任何问题")
            
            # 返回完整结果
            try:
                # 确保问卷数据有效
                if not generated_survey or not generated_survey.get('questions'):
                    raise ValueError("生成的问卷数据无效")
                
                # 清理数据，移除可能导致JSON序列化问题的字段
                clean_survey = {
                    "title": generated_survey.get("title", ""),
                    "description": generated_survey.get("description", ""),
                    "target_audience": generated_survey.get("target_audience", ""),
                    "estimated_time": generated_survey.get("estimated_time", 5),
                    "questions": generated_survey.get("questions", []),
                    "design_notes": generated_survey.get("design_notes", "")
                }
                
                response_data = {"type": "complete", "survey": clean_survey}
                response_json = json.dumps(response_data, ensure_ascii=False)
                
                # 确保JSON字符串是有效的
                # 验证JSON可以正确解析
                json.loads(response_json)
                
                yield f'data: {response_json}\n\n'
                print(f"[OK] Sent survey data, {len(clean_survey.get('questions', []))} questions")
                
            except json.JSONDecodeError as json_error:
                print(f"[ERROR] JSON serialization failed: {json_error}")
                import traceback
                traceback.print_exc()
                # 尝试更激进的清理
                try:
                    minimal_survey = {
                        "title": str(generated_survey.get("title", ""))[:200],
                        "description": str(generated_survey.get("description", ""))[:500],
                        "questions": []
                    }
                    # 只保留基本的问题字段
                    for q in generated_survey.get("questions", [])[:20]:  # 限制最多20个问题
                        clean_q = {
                            "id": q.get("id", 0),
                            "type": str(q.get("type", "单选题")),
                            "text": str(q.get("text", ""))[:500],
                            "required": bool(q.get("required", False))
                        }
                        if q.get("options"):
                            clean_q["options"] = [str(opt)[:200] for opt in q.get("options", [])[:10]]
                        if q.get("scale_min") is not None:
                            clean_q["scale_min"] = int(q.get("scale_min", 1))
                        if q.get("scale_max") is not None:
                            clean_q["scale_max"] = int(q.get("scale_max", 5))
                        minimal_survey["questions"].append(clean_q)
                    
                    minimal_response = {"type": "complete", "survey": minimal_survey}
                    minimal_json = json.dumps(minimal_response, ensure_ascii=False)
                    yield f'data: {minimal_json}\n\n'
                    print(f"[OK] Sent minimal survey data, {len(minimal_survey.get('questions', []))} questions")
                except Exception as e2:
                    print(f"[ERROR] Even minimal serialization failed: {e2}")
                    yield f'data: {{"type": "error", "message": "问卷数据序列化失败，请重试"}}\n\n'
            except Exception as json_error:
                print(f"[ERROR] Unexpected error during JSON serialization: {json_error}")
                import traceback
                traceback.print_exc()
                yield f'data: {{"type": "error", "message": "生成问卷时发生错误，请重试"}}\n\n'
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n[ERROR] Error occurred while generating survey:")
            # 避免Unicode编码错误，只打印ASCII字符
            try:
                print(error_trace)
            except UnicodeEncodeError:
                print("[ERROR] Error details (Unicode encoding issue)")
            
            # 提供更友好的错误提示
            error_msg = str(e)
            error_msg_lower = error_msg.lower()
            
            if "Connection" in error_msg or "10054" in error_msg or "远程主机" in error_msg:
                user_msg = "网络连接失败，请检查网络连接或稍后重试"
            elif "API key" in error_msg_lower or "authentication" in error_msg_lower:
                user_msg = "API Key 配置错误，请检查 .env 文件中的 DASHSCOPE_API_KEY"
            elif "timeout" in error_msg_lower or "timed out" in error_msg_lower:
                user_msg = "请求超时，请稍后重试或尝试更短的提示词"
            elif "403" in error_msg or "AllocationQuota" in error_msg or "quota" in error_msg_lower:
                # DashScope API配额限制
                if "Free" in error_msg or "free" in error_msg_lower:
                    user_msg = "API免费配额已用完。请前往阿里云DashScope控制台升级到付费套餐，或等待配额重置。\n\n解决方案：\n1. 访问 https://dashscope.console.aliyun.com/ 查看配额使用情况\n2. 升级到付费套餐以继续使用\n3. 免费配额通常每月重置，请稍后再试"
                else:
                    user_msg = "API配额已用完。请前往阿里云DashScope控制台查看配额使用情况并升级套餐。"
            elif "429" in error_msg or "rate limit" in error_msg_lower:
                user_msg = "API请求频率过高，请稍等片刻后重试"
            elif "401" in error_msg or "unauthorized" in error_msg_lower:
                user_msg = "API认证失败，请检查 .env 文件中的 DASHSCOPE_API_KEY 是否正确"
            else:
                # 截取错误消息的前200个字符，避免消息过长
                user_msg = f"生成问卷失败：{error_msg[:200]}"
            
            # 使用JSON安全序列化，避免SSE行中出现未转义的换行或引号导致前端解析失败
            error_payload = {"type": "error", "message": user_msg}
            yield f'data: {json.dumps(error_payload, ensure_ascii=False)}\n\n'
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


# 定义请求模型
from typing import Optional

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class SurveyRequest(BaseModel):
    survey: dict
    session_id: str = None

@app.post("/api/register")
async def register_api(request: RegisterRequest):
    """用户注册 API"""
    try:
        username = request.username.strip() if request.username else ""
        password = request.password or ""
        email = request.email.strip() if request.email else ""
        
        if not username or not password:
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "用户名和密码不能为空"}
            )
        
        if len(username) < 3 or len(username) > 20:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "用户名长度必须在3-20字符之间"}
            )
        
        if len(password) < 6:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "密码长度至少为6位"}
            )
        
        success = user_store.register(username, password, email if email else None)
        
        if success:
            return JSONResponse(content={"success": True, "message": "注册成功"})
        else:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "用户名已存在"}
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"注册失败: {str(e)}"}
        )


@app.post("/api/login")
async def login_api(request: LoginRequest):
    """用户登录 API"""
    try:
        username = request.username.strip() if request.username else ""
        password = request.password or ""
        
        if not username or not password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "用户名和密码不能为空"}
            )
        
        from app.models.user import User
        user = user_store.login(username, password)
        
        if user:
            session_id = session_manager.create_session(username)
            return JSONResponse(content={
                "success": True,
                "session_id": session_id,
                "username": username,
                "message": "登录成功"
            })
        else:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "用户名或密码错误"}
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"登录失败: {str(e)}"}
        )


class LogoutRequest(BaseModel):
    session_id: str

@app.post("/api/logout")
async def logout_api(request: LogoutRequest):
    """用户登出 API"""
    try:
        session_id = request.session_id or ""
        if session_id:
            session_manager.delete_session(session_id)
        return JSONResponse(content={"success": True})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"登出失败: {str(e)}"}
        )


@app.get("/api/user/surveys")
async def get_user_surveys_api(session_id: str = None):
    """获取用户的问卷列表"""
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    
    username = session_manager.get_username(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    surveys = user_survey_manager.get_user_surveys(username)
    
    return JSONResponse(content={
        "success": True,
        "surveys": surveys
    })


@app.delete("/api/user/surveys/{survey_id}")
async def delete_user_survey_api(survey_id: str, session_id: str = None):
    """删除用户的问卷"""
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    
    username = session_manager.get_username(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    try:
        # 从用户问卷列表中删除
        deleted = user_survey_manager.delete_survey(username, survey_id)
        if not deleted:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "问卷不存在或不属于当前用户"}
            )
        
        # 删除问卷文件
        from pathlib import Path
        surveys_dir = Path("data/surveys")
        
        # 查找并删除问卷文件
        survey_file = None
        for file_path in surveys_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    survey_data = json.load(f)
                    if survey_data.get("id") == survey_id:
                        survey_file = file_path
                        break
            except Exception:
                continue
        
        if survey_file and survey_file.exists():
            survey_file.unlink()
        
        # 删除回答数据目录
        responses_dir = Path("data/responses")
        if responses_dir.exists():
            for item in responses_dir.iterdir():
                if item.is_dir() and survey_id in item.name:
                    import shutil
                    shutil.rmtree(item)
                    break
        
        return JSONResponse(content={
            "success": True,
            "message": "问卷删除成功"
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"删除问卷失败: {str(e)}"}
        )


@app.get("/api/user/info")
async def get_user_info(session_id: str = None):
    """获取用户信息"""
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")
    
    username = session_manager.get_username(session_id)
    if not username:
        raise HTTPException(status_code=401, detail="会话已过期，请重新登录")
    
    return JSONResponse(content={
        "success": True,
        "username": username
    })


@app.post("/api/save-survey")
async def save_survey_api(request: dict):
    """发布问卷 API"""
    import uuid
    import re
    import traceback
    
    try:
        survey_data = request.get("survey", {})
        session_id = request.get("session_id", "")
        
        if not survey_data:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "问卷数据为空，请重新生成问卷"}
            )
        
        # 生成问卷ID
        survey_id = str(uuid.uuid4())[:8]
        survey_data["id"] = survey_id
        survey_data["created_at"] = datetime.now().isoformat()
        
        # 保存到内存和文件
        global surveys_storage
        surveys_storage[survey_id] = survey_data
        
        # 如果用户已登录，关联到用户
        if session_id:
            try:
                username = session_manager.get_username(session_id)
                if username:
                    survey_title = survey_data.get("title", "未命名问卷")
                    user_survey_manager.add_survey(username, survey_id, survey_title)
            except Exception as user_error:
                print(f"关联用户失败: {user_error}")
                # 即使关联失败，仍然发布问卷
        
        # 获取问卷标题并清理文件名
        survey_title = survey_data.get("title", "")
        def sanitize_filename(name: str, max_length: int = 50) -> str:
            sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
            sanitized = sanitized.strip('. ')
            if len(sanitized) > max_length:
                sanitized = sanitized[:max_length]
            return sanitized
        
        # 保存到文件，文件名包含问卷标题
        from pathlib import Path
        surveys_dir = Path("data/surveys")
        surveys_dir.mkdir(parents=True, exist_ok=True)
        
        if survey_title:
            clean_title = sanitize_filename(survey_title)
            filename = f"{clean_title}_{survey_id}.json"
        else:
            filename = f"{survey_id}.json"
        
        file_path = surveys_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(survey_data, f, ensure_ascii=False, indent=2)
        
        print(f"[发布问卷] 成功发布问卷: {survey_id}, 文件: {filename}")
        
        return JSONResponse(content={
            "success": True,
            "survey_id": survey_id, 
            "message": "Survey published successfully"
        })
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        traceback.print_exc()
        print(f"[发布问卷] 错误: {error_msg}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"发布问卷失败: {error_msg}"
            }
        )


@app.post("/api/submit-response")
async def submit_response_api(request: dict):
    """提交问卷答案 API"""
    import uuid
    
    survey_id = request.get("survey_id")
    answers = request.get("answers", {})
    user_id = request.get("user_id", str(uuid.uuid4())[:8])  # 如果没有提供user_id，则生成一个
    
    if not survey_id or not answers:
        raise HTTPException(status_code=400, detail="Survey ID and answers are required")
    
    # 获取问卷信息，以便在答案中包含问卷标题
    survey_info = {}
    survey_name = None
    
    # 查找问卷文件（可能包含标题作为前缀）
    surveys_dir = Path("data/surveys")
    survey_file = None
    if surveys_dir.exists():
        # 首先尝试直接查找 survey_id
        survey_file = surveys_dir / f"{survey_id}.json"
        if not survey_file.exists():
            # 查找所有包含该survey_id的文件
            for file_path in surveys_dir.glob(f"*_{survey_id}.json"):
                survey_file = file_path
                break
    
    if survey_file and survey_file.exists():
        with open(survey_file, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
            survey_info = {
                "title": survey_data.get("title", ""),
                "description": survey_data.get("description", "")
            }
            survey_name = survey_data.get("title", "")
    
    # 构建答案数据（包含问卷信息）
    response_data = {
        "survey_id": survey_id,
        "survey_info": survey_info,
        "submitted_at": datetime.now().isoformat(),
        "answers": answers
    }
    
    # 保存答案（会自动添加user_id和问卷名称）
    file_path = response_saver.save_response(survey_id, response_data, user_id, survey_name)
    
    return JSONResponse(content={
        "message": "Response submitted successfully",
        "file_path": file_path,
        "user_id": user_id
    })


@app.get("/api/survey/{survey_id}")
async def get_survey_by_id(survey_id: str):
    """根据ID获取问卷"""
    global surveys_storage
    
    if survey_id in surveys_storage:
        return JSONResponse(content=surveys_storage[survey_id])
    
    # 从文件加载
    from pathlib import Path
    surveys_dir = Path("data/surveys")
    
    # 首先尝试直接查找 {survey_id}.json（向后兼容）
    survey_file = surveys_dir / f"{survey_id}.json"
    
    # 如果不存在，查找包含该 survey_id 的文件
    if not survey_file.exists():
        for file_path in surveys_dir.glob(f"*_{survey_id}.json"):
            survey_file = file_path
            break
    
    # 如果还是找不到，尝试查找所有文件并匹配ID
    if not survey_file.exists():
        for file_path in surveys_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    temp_data = json.load(f)
                    if temp_data.get("id") == survey_id:
                        survey_file = file_path
                        break
            except:
                continue
    
    if survey_file.exists():
        with open(survey_file, 'r', encoding='utf-8') as f:
            import json
            survey_data = json.load(f)
            surveys_storage[survey_id] = survey_data
            return JSONResponse(content=survey_data)
    
    raise HTTPException(status_code=404, detail="Survey not found")


@app.get("/api/survey/{survey_id}/stats")
async def get_survey_stats(survey_id: str):
    """获取问卷统计数据"""
    stats = response_saver.get_statistics(survey_id)
    return JSONResponse(content=stats)


@app.post("/api/analyze/{survey_id}")
async def analyze_survey_results(survey_id: str, request: FastAPIRequest):
    """分析问卷结果 API - 支持开放题分析和全量分析两种模式"""
    try:
        # 获取请求体参数
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        analysis_type = body.get("analysis_type", "open_ended")  # 默认仅开放题分析
        
        print(f"\n[分析API] 开始分析问卷: {survey_id}, 分析类型: {analysis_type}")
        
        if analysis_type == "full":
            # 全量分析模式
            from app.services.full_analysis_service import FullAnalysisService
            from app.services.analysis_engine import SurveyAnalysisEngine
            
            # 使用SurveyAnalysisEngine加载数据
            engine = SurveyAnalysisEngine(llm_model="qwen-flash")
            survey, responses = engine._load_data(survey_id)
            
            if not responses:
                raise ValueError(f"问卷 {survey_id} 没有找到回答数据")
            
            # 执行全量分析
            full_analyzer = FullAnalysisService(llm_model="qwen-flash", temperature=0.3)
            full_analysis_result = full_analyzer.analyze_full_survey(survey, responses)
            
            result = {
                "survey_id": survey_id,
                "survey_title": survey.get("title", ""),
                "total_responses": len(responses),
                "analysis_type": "全量分析",
                "status": "success",
                "report_markdown": full_analysis_result["report_markdown"],
                "visualizations": full_analysis_result.get("visualizations", {}),
                "is_complete": full_analysis_result.get("is_complete", True)
            }
        else:
            # 仅开放题分析模式（原有逻辑）
            from app.services.analysis_engine import SurveyAnalysisEngine
            
            analyzer = SurveyAnalysisEngine(
                llm_model="qwen-flash",
                temperature=0.7
            )
            
            result = analyzer.analyze(survey_id)
        
        # 保存结果
        from pathlib import Path
        analyses_dir = Path("data/analyses")
        analyses_dir.mkdir(parents=True, exist_ok=True)
        analysis_file = analyses_dir / f"analysis_{survey_id}_{analysis_type}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"[分析API] 分析完成，结果已保存")
        
        return JSONResponse(content={
            "success": True,
            "survey_id": survey_id,
            **result
        })
        
    except FileNotFoundError as e:
        error_msg = f"问卷不存在或未找到回答数据: {str(e)}"
        print(f"[分析API] 错误: {error_msg}")
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": error_msg}
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_msg = f"分析失败: {str(e)}"
        print(f"[分析API] 错误: {error_msg}")
        print(f"[分析API] 错误堆栈:\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": error_msg}
        )


@app.get("/survey/{survey_id}", response_class=HTMLResponse)
async def survey_detail_page(survey_id: str, action: str = None):
    """问卷详情页面"""
    try:
        # 加载问卷数据
        from pathlib import Path
        surveys_dir = Path("data/surveys")
        
        # 查找问卷文件
        survey_file = None
        for file_path in surveys_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    survey_data = json.load(f)
                    if survey_data.get("id") == survey_id:
                        survey_file = file_path
                        break
            except Exception:
                continue
        
        if not survey_file or not survey_file.exists():
            return HTMLResponse(content="<h1>问卷不存在</h1><p>找不到指定的问卷</p>", status_code=404)
        
        # 读取问卷数据
        with open(survey_file, 'r', encoding='utf-8') as f:
            survey_data = json.load(f)
        
        # 根据action参数返回不同页面
        if action == "analyze":
            # 分析页面
            return HTMLResponse(content=get_analysis_page_html(survey_data))
        else:
            # 查看页面
            return HTMLResponse(content=get_survey_detail_html(survey_data))
            
    except Exception as e:
        return HTMLResponse(content=f"<h1>错误</h1><p>加载问卷失败: {str(e)}</p>", status_code=500)


@app.get("/fill/{survey_id}", response_class=HTMLResponse)
async def fill_survey_page(survey_id: str):
    """独立的问卷填写页面"""
    # 加载问卷数据
    from pathlib import Path
    surveys_dir = Path("data/surveys")
    
    # 首先尝试直接查找 {survey_id}.json（向后兼容）
    survey_file = surveys_dir / f"{survey_id}.json"
    
    # 如果不存在，查找包含该 survey_id 的文件
    if not survey_file.exists():
        for file_path in surveys_dir.glob(f"*_{survey_id}.json"):
            survey_file = file_path
            break
    
    # 如果还是找不到，尝试查找所有文件并匹配ID
    if not survey_file.exists():
        for file_path in surveys_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    temp_data = json.load(f)
                    if temp_data.get("id") == survey_id:
                        survey_file = file_path
                        break
            except:
                continue
    
    if not survey_file.exists():
        return HTMLResponse(content="<h1>问卷不存在</h1>", status_code=404)
    
    with open(survey_file, 'r', encoding='utf-8') as f:
        survey_data = json.load(f)
    
    # 生成填写页面HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{survey_data.get('title', '问卷填写')}</title>
        <link rel="stylesheet" href="/static/style.css">
        <script>
            window.surveyData = {json.dumps(survey_data, ensure_ascii=False)};
            window.surveyId = '{survey_id}';
        </script>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <h1>{survey_data.get('title', '问卷')}</h1>
                <p>请认真填写以下问卷</p>
            </header>
            
            <main class="main-content">
                <section class="result-section" style="display: block;">
                    <div id="surveyResult"></div>
                </section>
            </main>
        </div>
        <script src="/static/fill_survey.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


def cleanup_sessions():
    """定期清理过期会话"""
    session_manager.cleanup_expired()
    print(f"[CLEANUP] 会话清理完成，当前活跃会话数: {len(session_manager.sessions)}")


def start_scheduler():
    """启动定时任务"""
    # 每小时清理一次过期会话
    schedule.every().hour.do(cleanup_sessions)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[OK] 定时任务已启动")


def open_browser_with_port(port=8002):
    """延迟打开浏览器"""
    webbrowser.open(f'http://localhost:{port}')

def open_browser():
    """延迟打开浏览器（默认端口）"""
    open_browser_with_port(8002)


def get_survey_detail_html(survey_data):
    """生成问卷详情页面HTML"""
    questions_html = ""
    for i, question in enumerate(survey_data.get("questions", []), 1):
        qtype = question.get("type", "单选题")
        required = "（必答）" if question.get("required", False) else ""
        
        questions_html += f"""
        <div class="question-item">
            <h4>问题 {i} {required}</h4>
            <p class="question-text">{escape_html(question.get("text", ""))}</p>
            <p class="question-type">类型：{qtype}</p>
        """
        
        if qtype in ["单选题", "多选题"]:
            options = question.get("options", [])
            if options:
                questions_html += '<ul class="options-list">'
                for option in options:
                    questions_html += f"<li>{escape_html(option)}</li>"
                questions_html += "</ul>"
        elif qtype == "量表题":
            scale_min = question.get("scale_min", 1)
            scale_max = question.get("scale_max", 5)
            min_label = question.get("scale_min_label", "")
            max_label = question.get("scale_max_label", "")
            questions_html += f"""
            <div class="scale-info">
                <p>量表范围：{scale_min} - {scale_max}</p>
                {f'<p>最小值标签：{escape_html(min_label)}</p>' if min_label else ''}
                {f'<p>最大值标签：{escape_html(max_label)}</p>' if max_label else ''}
            </div>
            """
        
        questions_html += "</div>"
    
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>问卷详情 - {escape_html(survey_data.get("title", ""))}</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            .survey-detail-container {{
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .survey-header {{
                background: var(--bg-secondary);
                padding: 24px;
                border-radius: 12px;
                margin-bottom: 24px;
            }}
            .survey-title {{
                font-size: 24px;
                font-weight: 700;
                margin-bottom: 12px;
                color: var(--text-primary);
            }}
            .survey-meta {{
                display: flex;
                gap: 20px;
                margin-bottom: 16px;
                color: var(--text-secondary);
            }}
            .action-buttons {{
                display: flex;
                gap: 8px;
                margin-top: 20px;
                flex-wrap: nowrap;
                justify-content: flex-start;
                align-items: center;
                overflow-x: auto;
            }}
            .action-buttons button {{
                flex: 0 0 auto;
                min-width: 80px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
                white-space: nowrap;
                border-radius: 6px;
                border: 1px solid var(--border-color);
                background: var(--bg-primary);
                color: var(--text-primary);
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .action-buttons button:hover {{
                background: var(--bg-secondary);
                border-color: #667eea;
                transform: translateY(-1px);
            }}
            .action-buttons button:active {{
                transform: translateY(0);
            }}
            @media (max-width: 768px) {{
                .action-buttons {{
                    gap: 6px;
                    overflow-x: auto;
                }}
                .action-buttons button {{
                    min-width: 70px;
                    padding: 6px 10px;
                    font-size: 12px;
                }}
                .header h1 {{
                    font-size: 24px !important;
                }}
                .header p {{
                    font-size: 14px !important;
                }}
                .btn-secondary {{
                    padding: 6px 10px !important;
                    font-size: 12px !important;
                }}
            }}
            @media (max-width: 480px) {{
                .action-buttons {{
                    gap: 4px;
                    overflow-x: auto;
                }}
                .action-buttons button {{
                    min-width: 60px;
                    padding: 6px 8px;
                    font-size: 11px;
                }}
            }}
            .question-item {{
                background: var(--bg-secondary);
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 16px;
            }}
            .question-text {{
                font-size: 16px;
                margin-bottom: 12px;
                line-height: 1.5;
            }}
            .question-type {{
                color: var(--text-secondary);
                font-size: 14px;
                margin-bottom: 8px;
            }}
            .options-list {{
                list-style: none;
                padding: 0;
            }}
            
            /* 浮动返回按钮 */
            .floating-back-btn {{
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 56px;
                height: 56px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 50%;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                color: white;
                transition: all 0.3s ease;
                z-index: 1000;
                opacity: 0;
                visibility: hidden;
            }}
            
            .floating-back-btn.show {{
                opacity: 1;
                visibility: visible;
            }}
            
            .floating-back-btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }}
            
            .floating-back-btn:active {{
                transform: translateY(-1px);
            }}
            
            /* 底部固定按钮组 */
            .bottom-fixed-buttons {{
                position: fixed;
                bottom: 0;
                left: 50%;
                transform: translateX(-50%) translateY(100%);
                max-width: 800px;
                width: calc(100% - 40px);
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                border-top: 1px solid var(--border-color);
                border-left: 1px solid var(--border-color);
                border-right: 1px solid var(--border-color);
                border-radius: 12px 12px 0 0;
                padding: 16px 24px;
                display: flex;
                gap: 12px;
                justify-content: center;
                align-items: center;
                box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
                z-index: 999;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }}
            
            .bottom-fixed-buttons.show {{
                opacity: 1;
                visibility: visible;
                transform: translateX(-50%) translateY(0);
            }}
            
            .bottom-fixed-buttons button {{
                flex: 0 0 auto;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            
            .bottom-fixed-buttons .btn-primary {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            
            .bottom-fixed-buttons .btn-secondary {{
                background: white;
                color: var(--text-primary);
                border: 1px solid var(--border-color);
            }}
            
            .bottom-fixed-buttons button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }}
            
            /* 给内容底部添加padding，避免被固定按钮遮挡 */
            .survey-detail-container {{
                padding-bottom: 100px;
            }}
            
            @media (max-width: 768px) {{
                .floating-back-btn {{
                    width: 48px;
                    height: 48px;
                    bottom: 20px;
                    right: 20px;
                    font-size: 20px;
                }}
                
                .bottom-fixed-buttons {{
                    width: calc(100% - 24px);
                    padding: 12px 16px;
                    gap: 8px;
                    border-radius: 8px 8px 0 0;
                }}
                
                .bottom-fixed-buttons button {{
                    padding: 8px 14px;
                    font-size: 13px;
                }}
            }}
            
            @media (max-width: 480px) {{
                .bottom-fixed-buttons {{
                    width: calc(100% - 16px);
                    padding: 10px 12px;
                    gap: 6px;
                    flex-wrap: nowrap;
                    overflow-x: auto;
                }}
                
                .bottom-fixed-buttons button {{
                    padding: 8px 12px;
                    font-size: 12px;
                    white-space: nowrap;
                    min-width: fit-content;
                }}
            }}
            .options-list li {{
                padding: 8px 12px;
                background: rgba(102, 126, 234, 0.1);
                margin-bottom: 4px;
                border-radius: 4px;
            }}
            .scale-info {{
                background: rgba(102, 126, 234, 0.05);
                padding: 12px;
                border-radius: 6px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="survey-detail-container">
                <div class="survey-header">
                    <h1 class="survey-title">{escape_html(survey_data.get("title", ""))}</h1>
                    <div class="survey-meta">
                        <span>创建时间：{survey_data.get("created_at", "未知")}</span>
                        <span>预计时间：{survey_data.get("estimated_time", 5)} 分钟</span>
                        <span>问题数量：{len(survey_data.get("questions", []))}</span>
                    </div>
                    <p class="survey-description">{escape_html(survey_data.get("description", ""))}</p>
                    
                    <div class="action-buttons">
                        <button onclick="analyzeSurvey()">📊 分析结果</button>
                        <button onclick="shareSurvey()">🔗 分享</button>
                        <button onclick="window.location.href='/workspace'">📋 工作空间</button>
                    </div>
                </div>
                
                <div class="questions-section">
                    <h2>问题列表</h2>
                    {questions_html}
                </div>
            </div>
        </div>
        
        <!-- 浮动返回顶部按钮 -->
        <button class="floating-back-btn" id="backToTopBtn" title="返回顶部">
            ↑
        </button>
        
        <!-- 底部固定操作按钮 -->
        <div class="bottom-fixed-buttons" id="bottomButtons">
            <button class="btn-primary" onclick="window.location.href='/workspace'">
                🏠 返回工作空间
            </button>
            <button class="btn-secondary" onclick="analyzeSurvey()">
                📊 分析结果
            </button>
            <button class="btn-secondary" onclick="shareSurvey()">
                🔗 分享链接
            </button>
        </div>
        
        <script>
            const surveyId = "{survey_data.get("id", "")}";
            
            function analyzeSurvey() {{
                window.location.href = `/survey/${{surveyId}}?action=analyze`;
            }}
            
            function shareSurvey() {{
                const url = `${{window.location.origin}}/fill/${{surveyId}}`;
                navigator.clipboard.writeText(url);
                alert('分享链接已复制到剪贴板！');
            }}
            
            // 滚动监听，显示/隐藏按钮
            (function() {{
                const backToTopBtn = document.getElementById('backToTopBtn');
                const bottomButtons = document.getElementById('bottomButtons');
                let lastScrollTop = 0;
                
                window.addEventListener('scroll', function() {{
                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                    const scrollHeight = document.documentElement.scrollHeight;
                    const clientHeight = document.documentElement.clientHeight;
                    
                    // 滚动超过200px时显示返回顶部按钮
                    if (scrollTop > 200) {{
                        backToTopBtn.classList.add('show');
                    }} else {{
                        backToTopBtn.classList.remove('show');
                    }}
                    
                    // 滚动到页面下半部分时显示底部按钮
                    if (scrollTop > 300) {{
                        bottomButtons.classList.add('show');
                    }} else {{
                        bottomButtons.classList.remove('show');
                    }}
                    
                    lastScrollTop = scrollTop;
                }});
                
                // 返回顶部功能
                backToTopBtn.addEventListener('click', function() {{
                    window.scrollTo({{
                        top: 0,
                        behavior: 'smooth'
                    }});
                }});
                
                // 初始检查
                if (window.pageYOffset > 200) {{
                    backToTopBtn.classList.add('show');
                }}
                if (window.pageYOffset > 300) {{
                    bottomButtons.classList.add('show');
                }}
            }})();
        </script>
    </body>
    </html>
    """


def get_analysis_page_html(survey_data):
    """生成问卷分析页面HTML"""
    survey_id = survey_data.get("id", "")
    survey_title = escape_html(survey_data.get("title", ""))
    
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>问卷分析 - {survey_title}</title>
        <link rel="stylesheet" href="/static/style.css">
        <style>
            .analysis-container {{
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
            }}
            .analysis-header {{
                background: var(--bg-secondary);
                padding: 24px;
                border-radius: 12px;
                margin-bottom: 24px;
                text-align: center;
            }}
            .analysis-controls {{
                background: var(--bg-secondary);
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
            }}
            .analysis-results {{
                background: var(--bg-secondary);
                padding: 24px;
                border-radius: 8px;
                min-height: 400px;
            }}
            .loading-analysis {{
                text-align: center;
                padding: 40px;
            }}
            .spinner {{
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .theme-card {{
                background: rgba(255, 255, 255, 0.8);
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 16px;
                border-left: 4px solid #667eea;
            }}
            .theme-card.positive {{
                border-left-color: #4caf50;
            }}
            .theme-card.negative {{
                border-left-color: #f44336;
            }}
            .theme-card.neutral {{
                border-left-color: #ff9800;
            }}
            .quote {{
                background: #f5f5f5;
                padding: 12px;
                border-radius: 6px;
                margin: 10px 0;
                font-style: italic;
                border-left: 3px solid #667eea;
            }}
            .markdown-content {{
                line-height: 1.8;
            }}
            .markdown-content h1 {{
                color: #2c3e50;
                margin: 24px 0 16px 0;
                font-size: 28px;
            }}
            .markdown-content h2 {{
                color: #34495e;
                margin: 20px 0 12px 0;
                font-size: 24px;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 8px;
            }}
            .markdown-content h3 {{
                color: #7f8c8d;
                margin: 16px 0 10px 0;
                font-size: 20px;
            }}
            .markdown-content h4 {{
                color: #95a5a6;
                margin: 14px 0 8px 0;
                font-size: 18px;
            }}
            .markdown-content ul {{
                margin-left: 24px;
                margin-bottom: 16px;
            }}
            .markdown-content li {{
                margin-bottom: 8px;
                line-height: 1.6;
            }}
            .markdown-content p {{
                margin-bottom: 16px;
                line-height: 1.8;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="analysis-container">
                <div class="analysis-header">
                    <h1>📊 问卷定性分析报告</h1>
                    <p>{survey_title}</p>
                </div>
                
                <div class="analysis-controls">
                    <div style="margin-bottom: 20px;">
                        <label style="font-size: 16px; font-weight: 600; margin-bottom: 12px; display: block;">
                            📊 选择分析类型
                        </label>
                        <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                            <label style="cursor: pointer; padding: 12px 20px; border: 2px solid #667eea; border-radius: 8px; background: white; transition: all 0.2s;">
                                <input type="radio" name="analysisType" value="open_ended" checked style="margin-right: 8px;">
                                <span style="font-weight: 500;">📝 开放题分析</span>
                                <p style="margin: 4px 0 0 24px; font-size: 12px; color: #666;">仅分析开放式问题的文本回答</p>
                            </label>
                            <label style="cursor: pointer; padding: 12px 20px; border: 2px solid #667eea; border-radius: 8px; background: white; transition: all 0.2s;">
                                <input type="radio" name="analysisType" value="full" style="margin-right: 8px;">
                                <span style="font-weight: 500;">🎯 全量分析</span>
                                <p style="margin: 4px 0 0 24px; font-size: 12px; color: #666;">综合分析所有题型，生成深度诊断报告</p>
                            </label>
                        </div>
                    </div>
                    <button id="startAnalysisBtn" class="btn-primary" style="padding: 12px 32px; font-size: 16px;">
                        🚀 开始分析
                    </button>
                    <p id="statusInfo" style="font-size: 12px; color: #999; margin-top: 10px;">准备就绪</p>
                </div>
                
                <div class="analysis-results" id="analysisResults">
                    <div class="loading-analysis">
                        <p>选择分析类型并点击"开始分析"按钮</p>
                        <div style="color: var(--text-secondary); font-size: 14px; margin-top: 16px; text-align: left; max-width: 600px; margin-left: auto; margin-right: auto;">
                            <p style="margin-bottom: 8px;"><strong>📝 开放题分析：</strong>专注于文本回答的主题识别和情感分析</p>
                            <p><strong>🎯 全量分析：</strong>综合所有题型，包括选择题、量表题和开放题，提供交叉洞察和战略建议</p>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <button class="btn-secondary" onclick="window.location.href='/survey/{survey_id}'">📋 返回问卷详情</button>
                    <button class="btn-secondary" onclick="window.location.href='/workspace'">🏠 返回工作空间</button>
                </div>
            </div>
        </div>
        
        <script>
            (function() {{
                'use strict';
                
                const surveyId = "{survey_id}";
                const startBtn = document.getElementById('startAnalysisBtn');
                const statusInfo = document.getElementById('statusInfo');
                const resultsDiv = document.getElementById('analysisResults');
                
                // 绑定开始分析按钮
                startBtn.addEventListener('click', async function() {{
                    // 获取选中的分析类型
                    const analysisType = document.querySelector('input[name="analysisType"]:checked').value;
                    const isFullAnalysis = analysisType === 'full';
                    
                    // 禁用按钮
                    startBtn.disabled = true;
                    startBtn.textContent = '分析中...';
                    statusInfo.textContent = '正在分析中，请稍候...';
                    statusInfo.style.color = '#667eea';
                    
                    // 显示加载动画
                    if (isFullAnalysis) {{
                        resultsDiv.innerHTML = `
                            <div class="loading-analysis">
                                <div class="spinner"></div>
                                <p>🎯 正在进行全量分析，请稍候...</p>
                                <p style="color: var(--text-secondary); font-size: 14px; margin-top: 10px;">
                                    正在执行：数据统计 → 交叉分析 → LLM深度洞察 → 生成战略建议
                                </p>
                                <p style="color: var(--text-secondary); font-size: 12px; margin-top: 10px;">
                                    ⏳ 全量分析较为复杂，可能需要1-2分钟，请耐心等待...
                                </p>
                            </div>
                        `;
                    }} else {{
                        resultsDiv.innerHTML = `
                            <div class="loading-analysis">
                                <div class="spinner"></div>
                                <p>📝 正在进行开放题分析，请稍候...</p>
                                <p style="color: var(--text-secondary); font-size: 14px; margin-top: 10px;">
                                    正在执行：数据预处理 → 主题编码 → 情感分析 → 内容分析
                                </p>
                                <p style="color: var(--text-secondary); font-size: 12px; margin-top: 10px;">
                                    ⏳ 这可能需要30-60秒，请耐心等待...
                                </p>
                            </div>
                        `;
                    }}
                    
                    try {{
                        // 调用分析API
                        const response = await fetch(`/api/analyze/${{surveyId}}`, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                analysis_type: analysisType
                            }})
                        }});
                        
                        const data = await response.json();
                        
                        if (data.success) {{
                            // 显示分析结果
                            if (isFullAnalysis) {{
                                displayFullAnalysisResults(data);
                            }} else {{
                                displayAnalysisResults(data);
                            }}
                            startBtn.disabled = false;
                            startBtn.textContent = '🔄 重新分析';
                            statusInfo.textContent = '分析完成';
                            statusInfo.style.color = '#4caf50';
                        }} else {{
                            throw new Error(data.message || '分析失败');
                        }}
                        
                    }} catch (error) {{
                        console.error('分析错误:', error);
                        resultsDiv.innerHTML = `
                            <div style="text-align: center; padding: 40px;">
                                <h3 style="color: #e74c3c;">❌ 分析失败</h3>
                                <p style="color: var(--text-secondary); margin: 20px 0;">${{error.message}}</p>
                                <button class="btn-primary" onclick="location.reload()">🔄 重试</button>
                            </div>
                        `;
                        startBtn.disabled = false;
                        startBtn.textContent = '🚀 开始分析';
                        statusInfo.textContent = '分析失败，请重试';
                        statusInfo.style.color = '#f44336';
                    }}
                }});
                
                // 显示分析结果
                function displayAnalysisResults(data) {{
                    const report = data.report;
                    let html = '';
                    
                    // 添加可视化图表
                    if (data.visualizations) {{
                        html += '<div class="visualizations-container" style="margin-bottom: 30px;">';
                        html += '<h2 style="text-align: center;">📊 数据可视化</h2>';
                        
                        // 词云图
                        if (data.visualizations.wordcloud) {{
                            html += `
                                <div style="text-align: center; margin: 20px 0;">
                                    <h3>🔠 主题词云</h3>
                                    <img src="${{data.visualizations.wordcloud}}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;" alt="词云图">
                                </div>
                            `;
                        }}
                        
                        // 主题分布图和情感分布图并排显示
                        html += '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">';
                        
                        if (data.visualizations.theme_distribution) {{
                            html += `
                                <div style="text-align: center;">
                                    <h3>📊 主题分布</h3>
                                    <img src="${{data.visualizations.theme_distribution}}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;" alt="主题分布图">
                                </div>
                            `;
                        }}
                        
                        if (data.visualizations.sentiment_distribution) {{
                            html += `
                                <div style="text-align: center;">
                                    <h3>😊 情感分布</h3>
                                    <img src="${{data.visualizations.sentiment_distribution}}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;" alt="情感分布图">
                                </div>
                            `;
                        }}
                        
                        html += '</div>'; // grid结束
                        html += '</div>'; // visualizations-container结束
                        html += '<hr style="margin: 30px 0; border: none; border-top: 2px solid #eee;">';
                    }}
                    
                    if (data.formatted_report) {{
                        // 如果有格式化报告，直接显示Markdown转换后的HTML
                        html += convertMarkdownToHTML(data.formatted_report);
                    }} else {{
                        // 否则使用结构化数据生成HTML
                        html += `
                            <div class="markdown-content">
                                <h2>📊 总体摘要</h2>
                                <p>${{report.summary}}</p>
                                
                                <h2>🎯 核心主题分析</h2>
                        `;
                        
                        // 按情感分组
                        const positiveThemes = report.themes.filter(t => t.sentiment === 'positive');
                        const negativeThemes = report.themes.filter(t => t.sentiment === 'negative');
                        const neutralThemes = report.themes.filter(t => t.sentiment === 'neutral');
                        
                        if (positiveThemes.length > 0) {{
                            html += '<h3>✅ 积极反馈主题</h3>';
                            positiveThemes.forEach(theme => {{
                                html += createThemeCard(theme, 'positive');
                            }});
                        }}
                        
                        if (negativeThemes.length > 0) {{
                            html += '<h3>⚠️ 需要关注的主题</h3>';
                            negativeThemes.forEach(theme => {{
                                html += createThemeCard(theme, 'negative');
                            }});
                        }}
                        
                        if (neutralThemes.length > 0) {{
                            html += '<h3>📋 中性反馈主题</h3>';
                            neutralThemes.forEach(theme => {{
                                html += createThemeCard(theme, 'neutral');
                            }});
                        }}
                        
                        html += `
                                <h2>💡 行动建议</h2>
                                <p>${{report.recommendation}}</p>
                            </div>
                        `;
                    }}
                    
                    resultsDiv.innerHTML = html;
                }}
                
                // 创建主题卡片
                function createThemeCard(theme, sentimentClass) {{
                    return `
                        <div class="theme-card ${{sentimentClass}}">
                            <h4>${{theme.theme}}</h4>
                            <div class="quote">"${{theme.quote}}"</div>
                            <p><strong>情感倾向:</strong> ${{getSentimentLabel(theme.sentiment)}}</p>
                            <p><strong>提及频次:</strong> ${{theme.count}}</p>
                            ${{theme.description ? `<p><strong>说明:</strong> ${{theme.description}}</p>` : ''}}
                        </div>
                    `;
                }}
                
                // 获取情感标签
                function getSentimentLabel(sentiment) {{
                    const labels = {{
                        'positive': '积极（Positive）',
                        'negative': '消极（Negative）',
                        'neutral': '中性（Neutral）'
                    }};
                    return labels[sentiment] || sentiment;
                }}
                
                // 显示全量分析结果
                function displayFullAnalysisResults(data) {{
                    let html = '';
                    
                    // 显示报告不完整警告（如果需要）
                    if (data.is_complete === false) {{
                        html += `
                            <div style="background: #fff3cd; border: 2px solid #ffc107; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
                                <h3 style="color: #856404; margin: 0 0 10px 0;">⚠️ 报告完整性提示</h3>
                                <p style="color: #856404; margin: 0;">
                                    由于分析内容较多，当前显示的报告可能不完整。
                                    建议<strong>下载PDF完整报告</strong>以获取全部分析内容。
                                </p>
                                <button onclick="downloadPDFReport()" style="
                                    margin-top: 15px;
                                    background: #007bff;
                                    color: white;
                                    border: none;
                                    padding: 10px 20px;
                                    border-radius: 5px;
                                    cursor: pointer;
                                    font-size: 14px;
                                ">
                                    📄 下载完整PDF报告
                                </button>
                            </div>
                        `;
                    }}
                    
                    // 1. 显示可视化图表（如果有）
                    if (data.visualizations && Object.keys(data.visualizations).length > 0) {{
                        html += '<div class="visualizations-container" style="margin-bottom: 40px; padding: 20px; background: #f8f9fa; border-radius: 8px;">';
                        html += '<h2 style="text-align: center; color: #2c3e50; margin-bottom: 30px;">📊 数据可视化</h2>';
                        
                        const vizKeys = Object.keys(data.visualizations);
                        
                        // 2.1 显示整体词云（如果有）
                        if (data.visualizations.overall_wordcloud) {{
                            html += `
                                <div style="text-align: center; margin: 30px 0; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                    <h3 style="color: #667eea;">🔠 整体主题词云</h3>
                                    <img src="${{data.visualizations.overall_wordcloud}}" style="max-width: 100%; border-radius: 8px;" alt="整体词云">
                                </div>
                            `;
                        }}
                        
                        // 2.2 显示每个问题的可视化
                        // 按题号分组（scale_q1, single_choice_q2, wordcloud_q3 等）
                        const questionViz = {{}};
                        vizKeys.forEach(key => {{
                            if (key !== 'overall_wordcloud') {{
                                const match = key.match(/_q(\\d+)$/);
                                if (match) {{
                                    const qNum = match[1];
                                    if (!questionViz[qNum]) questionViz[qNum] = [];
                                    questionViz[qNum].push({{key: key, type: key.split('_q')[0]}});
                                }}
                            }}
                        }});
                        
                        // 按题号顺序显示
                        const sortedQNums = Object.keys(questionViz).sort((a, b) => parseInt(a) - parseInt(b));
                        
                        sortedQNums.forEach(qNum => {{
                            const vizList = questionViz[qNum];
                            html += `<div style="margin: 30px 0; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">`;
                            html += `<h3 style="color: #764ba2; margin-bottom: 20px;">📋 问题 ${{qNum}} 数据可视化</h3>`;
                            
                            // 如果有多个图表，用网格布局
                            if (vizList.length > 1) {{
                                html += '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px;">';
                            }}
                            
                            vizList.forEach(viz => {{
                                const typeLabel = {{
                                    'scale': '📊 分数分布',
                                    'single_choice': '📊 选项分布',
                                    'multiple_choice': '📊 选择频次',
                                    'wordcloud': '🔠 主题词云',
                                    'themes': '📈 主题分布'
                                }}[viz.type] || '📊 图表';
                                
                                html += `
                                    <div style="text-align: center;">
                                        <h4 style="color: #555;">${{typeLabel}}</h4>
                                        <img src="${{data.visualizations[viz.key]}}" style="max-width: 100%; border: 1px solid #e0e0e0; border-radius: 8px;" alt="${{viz.type}}">
                                    </div>
                                `;
                            }});
                            
                            if (vizList.length > 1) {{
                                html += '</div>';
                            }}
                            
                            html += '</div>';
                        }});
                        
                        html += '</div>';
                    }}
                    
                    // 2. 显示Markdown报告
                    if (data.report_markdown) {{
                        html += '<div class="markdown-content" style="background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">';
                        html += convertMarkdownToHTML(data.report_markdown);
                        html += '</div>';
                    }} else {{
                        html += '<div style="text-align: center; padding: 40px;"><p>未能生成分析报告</p></div>';
                    }}
                    
                    resultsDiv.innerHTML = html;
                }}
                
                // PDF导出功能（使用浏览器打印）
                function downloadPDFReport() {{
                    // 使用浏览器的打印功能导出为PDF
                    alert('提示：请在打印对话框中选择"另存为PDF"选项来保存完整报告。');
                    window.print();
                }}
                
                // 简单的Markdown转HTML
                function convertMarkdownToHTML(markdown) {{
                    let html = markdown
                        .replace(/^# (.*)$/gim, '<h1>$1</h1>')
                        .replace(/^## (.*)$/gim, '<h2>$1</h2>')
                        .replace(/^### (.*)$/gim, '<h3>$1</h3>')
                        .replace(/^#### (.*)$/gim, '<h4>$1</h4>')
                        .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
                        .replace(/^[-*] (.+)$/gim, '<li>$1</li>')
                        .replace(/^\\d+\\. (.+)$/gim, '<li>$1</li>')
                        .replace(/\\n\\n/gim, '</p><p>');
                    
                    // 包装段落
                    html = '<div class="markdown-content"><p>' + html + '</p></div>';
                    
                    // 清理多余的标签
                    html = html.replace(/<p><h/gim, '<h').replace(/\\/h[1-6]><\\/p>/gim, '</h>');
                    
                    return html;
                }}
            }})();
        </script>
    </body>
    </html>
    """


def escape_html(text):
    """HTML转义"""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")


def main():
    """主函数"""
    print("=" * 70)
    print("AI Survey Generation and Analysis System - Web Interface")
    print("=" * 70)
    
    # 检查 API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n[ERROR] DASHSCOPE_API_KEY not found in environment variables")
        print("\n请在 .env 文件中配置您的 DashScope API Key:")
        print("DASHSCOPE_API_KEY=your_api_key_here")
        return
    
    print("\n[OK] DashScope API Key configured")
    
    # 启动时清理过期会话
    print("\n[INFO] 清理过期会话...")
    session_manager.cleanup_expired()
    print(f"[OK] 当前活跃会话数: {len(session_manager.sessions)}")
    
    # 启动定时任务
    start_scheduler()
    
    try:
        # 创建服务
        print("\n[INFO] Initializing survey generation service...")
        print("  Model: qwen-flash")
        print("  Temperature: 0.7")
        global service
        service = SurveyService(
            llm_model="qwen-max",  # 主模型用于需求分析
            temperature=0.7,
            retrieval_k=3
        )
        
        print("[OK] Service initialized successfully!")
        
        # 检查端口占用
        import socket
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('127.0.0.1', port)) == 0
        
        port = 8002
        if is_port_in_use(port):
            print(f"\n[WARN] 端口 {port} 已被占用，尝试使用其他端口...")
            for alt_port in range(8003, 8010):
                if not is_port_in_use(alt_port):
                    port = alt_port
                    print(f"[INFO] 使用端口 {port}")
                    break
            else:
                print(f"\n[ERROR] 无法找到可用端口 (8002-8009)")
                print("[TIP] 请关闭其他占用端口的程序，或手动指定端口")
                return
        
        # 启动服务器
        print(f"\n[INFO] Starting Web server...")
        print(f"URL: http://localhost:{port}")
        
        # 生产环境不自动打开浏览器
        if not IS_PRODUCTION:
            print("\n[INFO] Please open the URL in your browser")
            print("   Enter your survey requirements and click 'Generate Survey'")
            # 延迟3秒后打开浏览器（仅开发环境）
            Timer(3, lambda: open_browser_with_port(port)).start()
        else:
            print("\n[INFO] 生产环境模式，服务器已启动")
            print(f"[INFO] 允许的主机: {', '.join(ALLOWED_HOSTS)}")
        
        # 启动服务器
        # 生产环境使用 WARNING 日志级别
        log_level = "warning" if IS_PRODUCTION else "info"
        uvicorn.run(app, host="0.0.0.0", port=port, log_level=log_level)
        
    except Exception as e:
        print(f"\n[ERROR] Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n[TIPS] Troubleshooting:")
        print("1. Ensure DASHSCOPE_API_KEY is configured")
        print("2. Ensure all dependencies are installed")
        print("3. Check debug_failed_json.txt for JSON parsing issues")


@app.post("/api/upload-rag-material")
async def upload_rag_material(file: UploadFile = File(...)):
    """上传RAG语料文件API"""
    try:
        # 检查文件类型
        if not file.filename.lower().endswith('.pdf'):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "只支持PDF文件格式"}
            )
        
        # 创建rag_materials文件夹
        materials_dir = Path("rag_materials")
        materials_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成安全的文件名
        import re
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', file.filename)
        safe_filename = safe_filename.strip('. ')
        
        # 如果文件已存在，添加时间戳
        file_path = materials_dir / safe_filename
        if file_path.exists():
            name_part = file_path.stem
            ext_part = file_path.suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{name_part}_{timestamp}{ext_part}"
            file_path = materials_dir / safe_filename
        
        # 保存文件
        with open(file_path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        file_size = file_path.stat().st_size
        
        print(f"[上传] 文件已保存: {safe_filename} ({file_size / 1024 / 1024:.2f} MB)")
        
        # 自动更新向量数据库
        try:
            from app.core.vector_store import SurveyVectorStore
            
            vector_store = SurveyVectorStore(
                persist_directory="./data/chroma_db",
                collection_name="exemplary_surveys"
            )
            
            # 尝试加载现有向量存储
            try:
                vector_store.create_vector_store()
                is_new = False
            except:
                is_new = True
            
            # 加载并处理PDF（已经切分）
            documents = vector_store.load_and_split_pdf(str(file_path))
            
            if is_new:
                # 创建新的向量存储
                vector_store.create_vector_store(documents)
                vector_store.persist()
                print(f"[向量化] 向量数据库已创建，包含 {len(documents)} 个文档块")
            else:
                # 添加到现有向量存储（文档已经切分，直接添加）
                vector_store.vector_store.add_documents(documents)
                vector_store.persist()
                print(f"[向量化] 已添加到向量数据库，包含 {len(documents)} 个文档块")
            
            # 更新索引文件
            update_rag_index(safe_filename, file_path)
            
        except Exception as e:
            print(f"[警告] 向量数据库更新失败: {e}")
            # 文件已保存，但向量化失败，返回警告而不是错误
            return JSONResponse(content={
                "success": True,
                "message": f"文件上传成功，但向量数据库更新失败: {str(e)}",
                "filename": safe_filename,
                "size": file_size,
                "vectorized": False
            })
        
        return JSONResponse(content={
            "success": True,
            "message": "文件上传成功，向量数据库已更新",
            "filename": safe_filename,
            "size": file_size,
            "vectorized": True,
            "document_count": len(documents)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"上传失败: {str(e)}"}
        )


def update_rag_index(filename: str, file_path: Path):
    """更新RAG索引文件"""
    index_file = Path("rag_materials") / ".rag_index.json"
    
    # 加载现有索引
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {}
    
    # 计算文件哈希
    import hashlib
    file_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            file_hash.update(chunk)
    hash_value = file_hash.hexdigest()
    
    # 更新索引
    index[filename] = {
        "hash": hash_value,
        "size": file_path.stat().st_size,
        "modified": file_path.stat().st_mtime,
        "processed_at": datetime.now().isoformat()
    }
    index["_last_updated"] = datetime.now().isoformat()
    
    # 保存索引
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


@app.get("/api/rag-materials/list")
async def list_rag_materials():
    """获取已上传的RAG语料文件列表"""
    try:
        materials_dir = Path("rag_materials")
        index_file = materials_dir / ".rag_index.json"
        
        # 加载索引
        materials = []
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            # 提取文件信息（排除内部字段）
            for filename, info in index.items():
                if filename.startswith('_'):
                    continue
                
                file_path = materials_dir / filename
                if file_path.exists():
                    materials.append({
                        "filename": filename,
                        "size": info.get("size", file_path.stat().st_size),
                        "processed_at": info.get("processed_at"),
                        "modified": info.get("modified")
                    })
        else:
            # 如果没有索引，扫描文件夹
            for pdf_file in materials_dir.glob("*.pdf"):
                if pdf_file.is_file():
                    stat = pdf_file.stat()
                    materials.append({
                        "filename": pdf_file.name,
                        "size": stat.st_size,
                        "processed_at": None,
                        "modified": stat.st_mtime
                    })
        
        # 按处理时间排序（最近处理的在前）
        materials.sort(key=lambda x: x.get("processed_at") or "", reverse=True)
        
        return JSONResponse(content={
            "success": True,
            "materials": materials,
            "count": len(materials)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"获取列表失败: {str(e)}"}
        )


@app.get("/api/rag-materials/status")
async def get_rag_status():
    """获取向量数据库状态"""
    try:
        from app.core.vector_store import SurveyVectorStore
        
        vector_store = SurveyVectorStore(
            persist_directory="./data/chroma_db",
            collection_name="exemplary_surveys"
        )
        
        try:
            vector_store.create_vector_store()
            stats = vector_store.get_stats()
            
            return JSONResponse(content={
                "success": True,
                "status": stats
            })
        except Exception as e:
            return JSONResponse(content={
                "success": True,
                "status": {
                    "status": "未初始化",
                    "error": str(e)
                }
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"获取状态失败: {str(e)}"}
        )


if __name__ == "__main__":
    main()

