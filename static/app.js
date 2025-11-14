// 问卷生成和显示功能
let currentSurvey = null;

// 生成问卷
async function generateSurvey() {
    const generateBtn = document.getElementById('generateBtn');
    const loadingSection = document.getElementById('loadingSection');
    const resultSection = document.getElementById('resultSection');
    const surveyPrompt = document.getElementById('surveyPrompt');
    
    if (!surveyPrompt.value.trim()) {
        showNotification('请输入问卷需求描述', 'error');
        return;
    }
    
    generateBtn.disabled = true;
    generateBtn.textContent = '生成中...';
    loadingSection.style.display = 'block';
    resultSection.style.display = 'none';
    
    // 清空并显示思考过程
    const thinkingProcess = document.getElementById('thinkingProcess');
    const thinkingMessages = document.getElementById('thinkingMessages');
    if (thinkingProcess && thinkingMessages) {
        thinkingProcess.style.display = 'block';
        thinkingMessages.innerHTML = '';
    }
    
    // 初始化进度条
    updateProgress(0, '准备开始');
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: surveyPrompt.value.trim() })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let survey = null;
        let buffer = ''; // 用于处理跨chunk的数据
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                // 处理最后可能残留的数据
                if (buffer.trim()) {
                    const lines = buffer.split('\n');
                    for (const line of lines) {
                        if (line.trim() && line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'complete' && data.survey) {
                                    survey = data.survey;
                                }
                            } catch (e) {
                                console.error('解析最后的数据时出错:', e);
                            }
                        }
                    }
                }
                break;
            }
            
            // 将新数据添加到缓冲区
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            
            // 保留最后一个不完整的行在缓冲区中
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.trim() && line.startsWith('data: ')) {
                    try {
                        const jsonStr = line.slice(6).trim();
                        if (!jsonStr) continue;
                        
                        const data = JSON.parse(jsonStr);
                        
                        if (data.type === 'step') {
                            document.getElementById('loadingStatus').textContent = data.message;
                            // 根据步骤更新进度条
                            updateProgressForStep(data.message);
                        } else if (data.type === 'progress') {
                            // 处理新的进度更新
                            updateProgress(data.progress, data.message);
                        } else if (data.type === 'thinking') {
                            showThinkingMessage(data.message);
                            // 思考过程中也逐步增加进度
                            incrementProgress();
                        } else if (data.type === 'complete') {
                            if (data.survey) {
                                survey = data.survey;
                                updateProgress(100, '问卷生成完成');
                                console.log('收到完整问卷数据:', survey);
                            } else {
                                console.error('收到complete消息但survey为空:', data);
                            }
                        } else if (data.type === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        console.error('解析SSE数据时出错:', e);
                        console.error('原始数据:', line);
                        // 如果是JSON解析错误，尝试继续处理，不中断流程
                        if (e instanceof SyntaxError) {
                            console.warn('JSON解析失败，跳过该行数据');
                        } else {
                            // 其他错误可能需要抛出
                            throw e;
                        }
                    }
                }
            }
        }
        
        if (survey && survey.questions && survey.questions.length > 0) {
            currentSurvey = survey;
            // 显示问卷编辑界面，允许用户修改
            showEditStep(survey);
        } else {
            console.error('未收到完整的问卷数据，survey:', survey);
            throw new Error('未收到完整的问卷数据。请检查网络连接或稍后重试。');
        }
        
    } catch (error) {
        console.error('Error:', error);
        const errorMessage = error.message || '未知错误';
        showNotification('生成问卷时出错: ' + errorMessage, 'error');
        loadingSection.style.display = 'none';
        
        // 根据错误类型显示不同的处理建议
        const errorMsgLower = errorMessage.toLowerCase();
        if (errorMessage.includes('网络') || errorMessage.includes('连接')) {
            // 网络错误，添加重试按钮
            const retryBtn = document.createElement('button');
            retryBtn.textContent = '🔄 重试';
            retryBtn.className = 'btn-primary';
            retryBtn.style.marginTop = '16px';
            retryBtn.addEventListener('click', function() {
                generateBtn.click();
            });
            loadingSection.appendChild(retryBtn);
        } else if (errorMessage.includes('配额') || errorMessage.includes('quota') || errorMessage.includes('AllocationQuota')) {
            // API配额错误，显示详细说明
            const errorInfo = document.createElement('div');
            errorInfo.style.cssText = 'margin-top: 16px; padding: 16px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; text-align: left;';
            errorInfo.innerHTML = `
                <h4 style="margin: 0 0 8px 0; color: #856404;">⚠️ API配额已用完</h4>
                <p style="margin: 0 0 12px 0; color: #856404; line-height: 1.6;">
                    ${errorMessage.replace(/\n/g, '<br>')}
                </p>
                <div style="margin-top: 12px;">
                    <a href="https://dashscope.console.aliyun.com/" target="_blank" 
                       style="display: inline-block; padding: 8px 16px; background: #007bff; color: white; 
                              text-decoration: none; border-radius: 4px; margin-right: 8px;">
                        🔗 前往DashScope控制台
                    </a>
                </div>
            `;
            loadingSection.appendChild(errorInfo);
        }
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '生成问卷';
    }
}

// 更新进度条
function updateProgress(percent, message) {
    const progressBarFill = document.getElementById('progressBarFill');
    const progressPercent = document.getElementById('progressPercent');
    const loadingStatus = document.getElementById('loadingStatus');
    
    // 平滑过渡效果
    if (progressBarFill) {
        progressBarFill.style.transition = 'width 0.5s ease-in-out';
        progressBarFill.style.width = percent + '%';
    }
    if (progressPercent) {
        progressPercent.textContent = Math.round(percent) + '%';
    }
    if (loadingStatus && message) {
        loadingStatus.textContent = message;
    }
    
    // 更新当前进度值
    currentProgress = percent;
}

// 根据步骤更新进度
function updateProgressForStep(stepMessage) {
    const stepProgressMap = {
        '正在分析您的需求...': 10,
        '需求优化完成': 25,
        '正在检索相关案例...': 40,
        '正在生成问卷内容...': 70,
        '问卷生成完成': 100
    };
    
    const progress = stepProgressMap[stepMessage] || 0;
    updateProgress(progress, stepMessage);
}

// 逐步增加进度
let currentProgress = 0;
function incrementProgress() {
    // 只有在没有明确进度更新时才使用随机增长
    if (currentProgress < 70) { // 在明确进度更新之前使用随机增长
        currentProgress += Math.random() * 2 + 0.5; // 随机增加0.5-2.5%
        updateProgress(Math.min(currentProgress, 70));
    }
}

// 生成问题预览HTML
function generateQuestionsPreview(questions) {
    if (!questions || questions.length === 0) {
        return '<p>暂无问题</p>';
    }
    
    return questions.map((question, index) => {
        // 使用displayNumber如果存在，否则使用index+1
        const questionNumber = question.displayNumber || (index + 1);
        let questionHtml = `
            <div class="question-preview">
                <h5>问题 ${questionNumber}: ${escapeHtml(question.text)}</h5>
                <p class="question-type">类型: ${question.type}</p>
        `;
        
        if (question.options && question.options.length > 0) {
            questionHtml += '<div class="options-preview">';
            question.options.forEach((option, optIndex) => {
                questionHtml += `<div class="option-item">${optIndex + 1}. ${escapeHtml(option)}</div>`;
            });
            questionHtml += '</div>';
        }
        
        if (question.scale_min !== undefined && question.scale_max !== undefined) {
            questionHtml += `
                <div class="scale-preview">
                    <span>${question.scale_min_label || question.scale_min}</span>
                    <span>${question.scale_max_label || question.scale_max}</span>
                </div>
            `;
        }
        
        questionHtml += '</div>';
        return questionHtml;
    }).join('');
}

// 显示问卷预览（带返回编辑按钮）
function showSurveyPreview(survey) {
    const loadingSection = document.getElementById('loadingSection');
    const resultSection = document.getElementById('resultSection');
    
    loadingSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    const html = `
        <div class="survey-preview">
            <div class="preview-header">
                <h2>📋 问卷预览</h2>
                <p>预览您的问卷效果，可以继续编辑或直接发布</p>
            </div>
            
            <div class="preview-content">
                <div class="survey-preview-info">
                    <h3>📋 ${escapeHtml(survey.title || '未命名问卷')}</h3>
                    <p class="survey-description">${escapeHtml(survey.description || '')}</p>
                    <div class="survey-meta">
                        <span>目标受众：${escapeHtml(survey.target_audience || '')}</span>
                        <span>预计时间：${survey.estimated_time || 5} 分钟</span>
                        <span>问题数量：${survey.questions ? survey.questions.length : 0}</span>
                    </div>
                    
                    <div class="questions-preview">
                        <h4>📝 问卷问题预览</h4>
                        ${generateQuestionsPreview(survey.questions || [])}
                    </div>
                </div>
                
                <div class="preview-actions">
                    <button id="backToEditBtn" class="btn-secondary btn-lg">✏️ 继续编辑</button>
                    <button id="publishFromPreviewBtn" class="btn-primary btn-lg">🚀 发布问卷</button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('surveyResult').innerHTML = html;
    
    // 等待DOM更新后滚动到页面顶部，让用户从上往下预览
    setTimeout(() => {
        // 滚动到页面顶部
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
        
        // 如果页面有滚动容器，也滚动容器到顶部
        const resultSection = document.getElementById('resultSection');
        if (resultSection) {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // 滚动文档主体到顶部
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
    }, 100);
    
    // 绑定事件
    document.getElementById('backToEditBtn').addEventListener('click', function() {
        // 返回编辑模式
        showEditStep(currentSurvey);
    });
    
    document.getElementById('publishFromPreviewBtn').addEventListener('click', function() {
        publishSurvey();
    });
}

// 显示问卷结果（只读模式）
function showSurveyResult(survey) {
    const loadingSection = document.getElementById('loadingSection');
    const resultSection = document.getElementById('resultSection');
    
    loadingSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    const html = `
        <div class="survey-result">
            <div class="result-header">
                <h2>🎉 问卷生成完成！</h2>
                <p>您的问卷已生成，可以发布并开始收集回答了</p>
            </div>
            
            <div class="result-content">
                <div class="survey-preview">
                    <h3>📋 ${escapeHtml(survey.title || '未命名问卷')}</h3>
                    <p class="survey-description">${escapeHtml(survey.description || '')}</p>
                    <div class="survey-meta">
                        <span>目标受众：${escapeHtml(survey.target_audience || '')}</span>
                        <span>预计时间：${survey.estimated_time || 5} 分钟</span>
                        <span>问题数量：${survey.questions ? survey.questions.length : 0}</span>
                    </div>
                    
                    <div class="questions-preview">
                        <h4>📝 问卷问题预览</h4>
                        ${generateQuestionsPreview(survey.questions || [])}
                </div>
            </div>
            
                <div class="action-buttons">
                    <button id="publishSurveyBtn" class="btn-primary btn-lg">发布问卷</button>
                    <button id="goToWorkspaceBtn" class="btn-secondary">返回工作空间</button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('surveyResult').innerHTML = html;
    
    // 绑定事件
    document.getElementById('publishSurveyBtn').addEventListener('click', function() {
        publishSurvey(survey);
    });
    
    document.getElementById('goToWorkspaceBtn').addEventListener('click', function() {
        window.location.href = '/workspace';
    });
}

// 发布问卷
async function publishSurvey(survey) {
    try {
        const sessionId = localStorage.getItem('session_id');
        
        console.log('开始发布问卷...', survey);
        
        const response = await fetch('/api/save-survey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                survey: survey,
                session_id: sessionId
            })
        });
        
        console.log('收到响应，状态码:', response.status, response.statusText);
        
        // 检查响应状态
        if (!response.ok) {
            let errorMessage = '发布失败';
            try {
                const errorData = await response.json();
                errorMessage = errorData.message || errorData.detail || `HTTP错误 ${response.status}`;
            } catch (e) {
                errorMessage = `HTTP错误 ${response.status}: ${response.statusText}`;
            }
            alert('发布问卷失败: ' + errorMessage);
            console.error('发布问卷失败:', errorMessage);
            return;
        }
        
        const data = await response.json();
        console.log('响应数据:', data);
        
        if (data.success !== false && data.survey_id) {
            showShareLink(data.survey_id);
        } else {
            alert('发布问卷失败: ' + (data.message || '未知错误'));
        }
    } catch (error) {
        console.error('发布问卷错误:', error);
        alert('发布问卷失败: ' + (error.message || '网络错误，请检查网络连接或稍后重试'));
    }
}

// 显示分享链接（通用函数，支持预览和编辑界面）
function showShareLink(surveyId) {
    const shareUrl = `${window.location.origin}/fill/${surveyId}`;
    
    // 优先查找 surveyResult，因为预览和编辑界面都是在这里显示
    const resultSection = document.getElementById('surveyResult');
    let container = resultSection;
    
    // 如果找不到 surveyResult，尝试查找其他容器
    if (!container) {
        container = document.querySelector('.survey-result') || 
                    document.querySelector('.survey-preview') || 
                    document.querySelector('.survey-editor');
    }
    
    if (!container) {
        console.error('找不到可用的容器来显示分享链接');
        alert('问卷发布成功！链接: ' + shareUrl);
        return;
    }
    
    container.innerHTML = `
            <div class="result-header">
            <h2>🎉 问卷发布成功！</h2>
                <p>您的问卷已发布，可以开始收集回答了</p>
            </div>
            
        <div class="result-content">
            <div class="share-section">
                <h3>📋 分享给受访者的填写链接</h3>
                <div class="share-link-container">
                    <input type="text" id="shareLink" value="${shareUrl}" readonly class="share-link-input">
                    <button onclick="copyShareLink()" class="btn-copy">复制链接</button>
                </div>
                <p class="share-tip">将链接分享给目标受众，他们可以通过此链接填写问卷</p>
            </div>
        </div>
    `;
}

// 复制分享链接
function copyShareLink() {
    const shareLink = document.getElementById('shareLink');
    shareLink.select();
    document.execCommand('copy');
    alert('链接已复制到剪贴板！');
}

// 显示思考消息
function showThinkingMessage(message) {
    const thinkingProcess = document.getElementById('thinkingProcess');
    const thinkingMessages = document.getElementById('thinkingMessages');
    
    if (!thinkingProcess || !thinkingMessages) return;
    
    // 确保思考过程区域可见
    thinkingProcess.style.display = 'block';
    
    // 创建消息元素
    const messageDiv = document.createElement('div');
    messageDiv.className = 'thinking-message';
    messageDiv.textContent = message;
    
    // 添加到消息容器
    thinkingMessages.appendChild(messageDiv);
    
    // 滚动到底部
    thinkingMessages.scrollTop = thinkingMessages.scrollHeight;
    
    // 限制消息数量，避免过多消息影响性能
    const messages = thinkingMessages.querySelectorAll('.thinking-message');
    if (messages.length > 20) {
        messages[0].remove();
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 改进的通知实现，支持多行消息
    if (type === 'error') {
        // 对于错误消息，使用更友好的显示方式
        // 将换行符转换为HTML换行，或使用alert（浏览器会自动处理换行）
        alert(message);
    } else {
        alert(message);
    }
}

// HTML转义
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 显示编辑步骤
function showEditStep(survey) {
    const loadingSection = document.getElementById('loadingSection');
    const resultSection = document.getElementById('resultSection');
    
    loadingSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    const html = `
        <div class="survey-editor">
            <div class="editor-header">
                <h2>📝 编辑问卷</h2>
                <p>您可以修改问卷内容，完成后点击发布</p>
            </div>
            
            <div class="editor-content">
                <div class="survey-info-section">
                    <h3>📋 问卷信息</h3>
                    <div class="info-item">
                    <label>问卷标题</label>
                        <input type="text" id="surveyTitle" value="${escapeHtml(survey.title || '')}" class="edit-input">
                </div>
                    <div class="info-item">
                    <label>问卷描述</label>
                        <textarea id="surveyDescription" class="edit-textarea" rows="2">${escapeHtml(survey.description || '')}</textarea>
                </div>
                    <div class="info-item">
                        <label>目标受众</label>
                        <input type="text" id="targetAudience" value="${escapeHtml(survey.target_audience || '')}" class="edit-input">
                </div>
            </div>
            
            <div class="questions-section">
                <div class="section-header">
                        <h3>❓ 问题列表</h3>
                        <button id="addQuestionBtn" class="btn-add">+ 添加问题</button>
                    </div>
                    <div id="questionsContainer" class="questions-container">
                        ${renderEditableQuestions(survey.questions || [])}
                    </div>
                </div>
                
                <div class="editor-actions">
                    <button id="previewBtn" class="btn-secondary">👁️ 预览</button>
                    <button id="publishBtn" class="btn-primary btn-large">🚀 发布问卷</button>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('surveyResult').innerHTML = html;
    
    // 绑定事件
    bindEditEvents();
}

// 渲染可编辑的问题列表
function renderEditableQuestions(questions, sortByNumber = false) {
    if (!questions || questions.length === 0) {
        return '<div class="no-questions">暂无问题，点击"添加问题"开始创建</div>';
    }
    
    // 如果需要按题号排序，创建排序后的副本
    let questionsToRender = questions;
    if (sortByNumber) {
        questionsToRender = [...questions].sort((a, b) => {
            const aNum = parseInt(a.id) || 0;
            const bNum = parseInt(b.id) || 0;
            return aNum - bNum;
        });
    }
    
    return questionsToRender.map((question, index) => {
        // 在编辑模式下，使用原始索引；在排序模式下，使用排序后的索引
        const displayIndex = sortByNumber ? questionsToRender.indexOf(question) : index;
        // 编辑时也按位置显示题号（最上面的是问题1）
        const questionNumber = index + 1;
        
        return `
        <div class="question-item" data-index="${displayIndex}">
            <div class="question-header">
                <span class="question-number">问题 ${questionNumber}</span>
                <div class="question-actions">
                    <button class="btn-move-up" onclick="moveQuestion(${displayIndex}, 'up')" title="上移">⬆️</button>
                    <button class="btn-move-down" onclick="moveQuestion(${displayIndex}, 'down')" title="下移">⬇️</button>
                    <button class="btn-delete" onclick="deleteQuestion(${displayIndex})" title="删除">🗑️</button>
                </div>
                </div>
                
            <div class="question-content">
                <div class="question-text">
                    <input type="text" value="${escapeHtml(question.text || '')}" 
                           class="edit-input question-text-input" 
                           data-field="text" data-index="${displayIndex}"
                           placeholder="请输入问题内容">
                </div>
                
                <div class="question-settings">
                    <div class="setting-item">
                        <label>类型</label>
                        <select class="edit-select question-type-select" data-field="type" data-index="${displayIndex}">
                            <option value="单选题" ${question.type === '单选题' ? 'selected' : ''}>单选题</option>
                            <option value="多选题" ${question.type === '多选题' ? 'selected' : ''}>多选题</option>
                            <option value="量表题" ${question.type === '量表题' ? 'selected' : ''}>量表题</option>
                            <option value="开放式问题" ${question.type === '开放式问题' ? 'selected' : ''}>开放式问题</option>
                        </select>
                    </div>
                    
                    <div class="setting-item">
                        <label>
                            <input type="checkbox" class="question-required-checkbox" 
                                   data-field="required" data-index="${displayIndex}" 
                                   ${question.required ? 'checked' : ''}>
                            必填
                        </label>
                    </div>
                </div>
                
                ${renderQuestionOptions(question, displayIndex)}
            </div>
        </div>
    `;
    }).join('');
}

// 生成量表预览
function generateScalePreview(question) {
    const min = parseInt(question.scale_min) || 1;
    const max = parseInt(question.scale_max) || 5;
    const minLabel = question.scale_min_label || '';
    const maxLabel = question.scale_max_label || '';
    
    let preview = '<div class="scale-preview-items">';
    
    for (let i = min; i <= max; i++) {
        preview += `<div class="scale-preview-item">${i}</div>`;
    }
    
    preview += '</div>';
    
    if (minLabel || maxLabel) {
        preview += '<div class="scale-preview-labels">';
        if (minLabel) preview += `<span class="scale-label-min">${minLabel}</span>`;
        if (maxLabel) preview += `<span class="scale-label-max">${maxLabel}</span>`;
        preview += '</div>';
    }
    
    return preview;
}

// 渲染问题选项
function renderQuestionOptions(question, index) {
    if (['单选题', '多选题'].includes(question.type)) {
        const options = question.options || ['选项1', '选项2'];
        return `
            <div class="question-options">
                <div class="options-header">
                    <label>选项</label>
                    <button class="btn-add-small" onclick="addOption(${index})">+ 添加选项</button>
                </div>
                <div class="options-list">
                    ${options.map((option, optIndex) => `
                    <div class="option-item">
                            <input type="text" value="${escapeHtml(option)}" 
                                   class="edit-input option-input" 
                                   data-field="options" data-index="${index}" data-option="${optIndex}">
                            <button class="btn-delete-small" onclick="deleteOption(${index}, ${optIndex})">×</button>
                    </div>
                    `).join('')}
                </div>
                </div>
            `;
        } else if (question.type === '量表题') {
        return `
            <div class="question-scale">
                <div class="scale-range-selector">
                    <label>量表范围</label>
                    <div class="range-slider-container">
                        <div class="range-display">
                            <span class="range-min">${question.scale_min || 1}</span>
                            <span class="range-separator">-</span>
                            <span class="range-max">${question.scale_max || 10}</span>
                        </div>
                        <div class="range-slider">
                            <input type="range" 
                                   class="range-input" 
                                   data-field="scale_min" 
                                   data-index="${index}"
                                   min="1" max="10" 
                                   value="${question.scale_min || 1}"
                                   oninput="updateScaleRange(${index}, 'min', this.value)">
                            <input type="range" 
                                   class="range-input" 
                                   data-field="scale_max" 
                                   data-index="${index}"
                                   min="1" max="10" 
                                   value="${question.scale_max || 10}"
                                   oninput="updateScaleRange(${index}, 'max', this.value)">
                        </div>
                        <div class="range-labels">
                            <span>1</span>
                            <span>10</span>
                        </div>
                    </div>
                </div>
                <div class="scale-preview">
                    <label>预览效果：</label>
                    <div class="scale-preview-display" data-index="${index}">
                        ${generateScalePreview(question)}
                    </div>
                </div>
            </div>
            `;
        }
    return '';
}

// 绑定编辑事件
function bindEditEvents() {
    // 问卷信息更新
    document.getElementById('surveyTitle').addEventListener('input', updateSurveyInfo);
    document.getElementById('surveyDescription').addEventListener('input', updateSurveyInfo);
    document.getElementById('targetAudience').addEventListener('input', updateSurveyInfo);
    
    // 问题内容更新
    document.querySelectorAll('.question-text-input').forEach(input => {
        input.addEventListener('input', function() {
            const index = parseInt(this.dataset.index);
            const field = this.dataset.field;
            updateQuestionField(index, field, this.value);
        });
    });
    
    // 问题类型更新
    document.querySelectorAll('.question-type-select').forEach(select => {
        select.addEventListener('change', function() {
            const index = parseInt(this.dataset.index);
            const field = this.dataset.field;
            updateQuestionField(index, field, this.value);
            // 重新渲染问题选项
            renderQuestionOptionsForIndex(index);
        });
    });
    
    // 必填状态更新
    document.querySelectorAll('.question-required-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const index = parseInt(this.dataset.index);
            const field = this.dataset.field;
            updateQuestionField(index, field, this.checked);
        });
    });
    
    // 选项更新
    document.querySelectorAll('.option-input').forEach(input => {
        input.addEventListener('input', function() {
            const index = parseInt(this.dataset.index);
            const optionIndex = parseInt(this.dataset.option);
            const field = this.dataset.field;
            updateQuestionOption(index, field, optionIndex, this.value);
        });
    });
    
    // 量表设置更新（移除，现在使用内联事件处理）
    // document.querySelectorAll('.scale-input').forEach(input => {
    //     input.addEventListener('input', function() {
    //         const index = parseInt(this.dataset.index);
    //         const field = this.dataset.field;
    //         let value = this.value;
    //         
    //         // 验证数值范围
    //         if (field === 'scale_min' || field === 'scale_max') {
    //             const numValue = parseInt(value);
    //             if (field === 'scale_min') {
    //                 if (numValue < 0) value = '0';
    //                 if (numValue > 100) value = '100';
    //             } else if (field === 'scale_max') {
    //                 if (numValue < 1) value = '1';
    //                 if (numValue > 100) value = '100';
    //             }
    //             this.value = value;
    //         }
    //         
    //         updateQuestionField(index, field, value);
    //         
    //         // 更新量表预览
    //         updateScalePreview(index);
    //     });
    // });
    
    // 按钮事件
    document.getElementById('addQuestionBtn').addEventListener('click', addNewQuestion);
    document.getElementById('previewBtn').addEventListener('click', previewSurvey);
    document.getElementById('publishBtn').addEventListener('click', publishSurvey);
}

// 更新问卷信息
function updateSurveyInfo() {
    if (!currentSurvey) return;
    
    // 检查元素是否存在（可能在预览界面，这些元素不存在）
    const titleElement = document.getElementById('surveyTitle');
    const descElement = document.getElementById('surveyDescription');
    const audienceElement = document.getElementById('targetAudience');
    
    if (titleElement) {
        currentSurvey.title = titleElement.value;
    }
    if (descElement) {
        currentSurvey.description = descElement.value;
    }
    if (audienceElement) {
        currentSurvey.target_audience = audienceElement.value;
    }
}

// 更新量表范围
function updateScaleRange(index, type, value) {
    if (!currentSurvey || !currentSurvey.questions) return;
    
    const question = currentSurvey.questions[index];
    const field = type === 'min' ? 'scale_min' : 'scale_max';
    const numValue = parseInt(value);
    
    // 确保最小值不大于最大值
    if (type === 'min' && numValue >= question.scale_max) {
        question.scale_max = numValue + 1;
        document.querySelector(`[data-index="${index}"][data-field="scale_max"]`).value = question.scale_max;
    } else if (type === 'max' && numValue <= question.scale_min) {
        question.scale_min = numValue - 1;
        document.querySelector(`[data-index="${index}"][data-field="scale_min"]`).value = question.scale_min;
    }
    
    question[field] = numValue;
    
    // 更新显示
    const rangeMin = document.querySelector(`[data-index="${index}"] .range-min`);
    const rangeMax = document.querySelector(`[data-index="${index}"] .range-max`);
    
    if (rangeMin) rangeMin.textContent = question.scale_min;
    if (rangeMax) rangeMax.textContent = question.scale_max;
    
    // 更新预览
    updateScalePreview(index);
}

// 更新量表预览
function updateScalePreview(index) {
    if (!currentSurvey || !currentSurvey.questions) return;
    
    const question = currentSurvey.questions[index];
    const previewDisplay = document.querySelector(`[data-index="${index}"] .scale-preview-display`);
    
    if (previewDisplay && question.type === '量表题') {
        previewDisplay.innerHTML = generateScalePreview(question);
    }
}

// 更新问题字段
function updateQuestionField(index, field, value) {
    if (!currentSurvey || !currentSurvey.questions) return;
    if (currentSurvey.questions[index]) {
        currentSurvey.questions[index][field] = value;
    }
}

// 更新问题选项
function updateQuestionOption(index, field, optionIndex, value) {
    if (!currentSurvey || !currentSurvey.questions) return;
    if (currentSurvey.questions[index] && currentSurvey.questions[index].options) {
        currentSurvey.questions[index].options[optionIndex] = value;
    }
}

// 重新渲染指定问题的选项
function renderQuestionOptionsForIndex(index) {
    if (!currentSurvey || !currentSurvey.questions) return;
    
    const question = currentSurvey.questions[index];
    const questionItem = document.querySelector(`[data-index="${index}"]`);
    if (questionItem) {
        const questionContent = questionItem.querySelector('.question-content');
        const existingOptions = questionContent.querySelector('.question-options, .question-scale');
        if (existingOptions) {
            existingOptions.remove();
        }
        
        const newOptions = renderQuestionOptions(question, index);
        if (newOptions) {
            questionContent.insertAdjacentHTML('beforeend', newOptions);
            bindEditEvents(); // 重新绑定事件
        }
    }
}

// 添加新问题
function addNewQuestion() {
    if (!currentSurvey) {
        currentSurvey = { questions: [] };
    }
    if (!currentSurvey.questions) {
        currentSurvey.questions = [];
    }
    
    // 生成新的题号，确保不重复
    const maxId = Math.max(...currentSurvey.questions.map(q => parseInt(q.id) || 0), 0);
    const newId = maxId + 1;
    
    const newQuestion = {
        id: newId,
        type: '单选题',
        text: '新问题',
        required: true,
        options: ['选项1', '选项2'],
        scale_min: 1,
        scale_max: 10
    };
    
    // 将新问题添加到数组开头（最上面）
    currentSurvey.questions.unshift(newQuestion);
    
    // 重新渲染问题列表
    const container = document.getElementById('questionsContainer');
    container.innerHTML = renderEditableQuestions(currentSurvey.questions);
    bindEditEvents();
}

// 移动问题位置
function moveQuestion(index, direction) {
    if (!currentSurvey || !currentSurvey.questions) return;
    
    const questions = currentSurvey.questions;
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    
    // 检查边界
    if (newIndex < 0 || newIndex >= questions.length) {
        return; // 不能移动
    }
    
    // 交换位置
    [questions[index], questions[newIndex]] = [questions[newIndex], questions[index]];
    
    // 重新渲染问题列表
    const container = document.getElementById('questionsContainer');
    container.innerHTML = renderEditableQuestions(questions);
    bindEditEvents();
}

// 删除问题
function deleteQuestion(index) {
    if (!currentSurvey || !currentSurvey.questions) return;
    if (confirm('确定要删除这个问题吗？')) {
        currentSurvey.questions.splice(index, 1);
        
        // 重新渲染问题列表
        const container = document.getElementById('questionsContainer');
        container.innerHTML = renderEditableQuestions(currentSurvey.questions);
        bindEditEvents();
    }
}

// 添加选项
function addOption(questionIndex) {
    if (!currentSurvey || !currentSurvey.questions) return;
    if (currentSurvey.questions[questionIndex]) {
        if (!currentSurvey.questions[questionIndex].options) {
            currentSurvey.questions[questionIndex].options = [];
        }
        currentSurvey.questions[questionIndex].options.push('新选项');
        
        // 重新渲染问题选项
        renderQuestionOptionsForIndex(questionIndex);
    }
}

// 删除选项
function deleteOption(questionIndex, optionIndex) {
    if (!currentSurvey || !currentSurvey.questions) return;
    if (currentSurvey.questions[questionIndex] && currentSurvey.questions[questionIndex].options) {
        currentSurvey.questions[questionIndex].options.splice(optionIndex, 1);
        
        // 重新渲染问题选项
        renderQuestionOptionsForIndex(questionIndex);
    }
}

// 预览问卷
function previewSurvey() {
    if (!currentSurvey) return;
    
    // 更新当前问卷信息
    updateSurveyInfo();
    
    // 创建按位置排序的问卷副本用于预览（最上面的是问题1）
    const sortedSurvey = {
        ...currentSurvey,
        questions: [...currentSurvey.questions].map((question, index) => ({
            ...question,
            displayNumber: index + 1  // 按位置重新编号
        }))
    };
    
    // 显示预览
    showSurveyPreview(sortedSurvey);
    
    // 确保滚动到顶部（双重保险）
    setTimeout(() => {
        // 尝试多种滚动方式以确保生效
        if (window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop) {
            window.scrollTo(0, 0);
        }
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
        
        // 如果页面有结果区域，滚动到该区域顶部
        const resultSection = document.getElementById('resultSection');
        if (resultSection) {
            resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, 200);
}

// 发布问卷
async function publishSurvey() {
    if (!currentSurvey) {
        alert('当前没有可发布的问卷，请先生成问卷');
        return;
    }
    
    try {
        // 更新当前问卷信息
        updateSurveyInfo();
        
        // 创建按位置排序的问卷副本用于发布（最上面的是问题1）
        const sortedSurvey = {
            ...currentSurvey,
            questions: [...currentSurvey.questions].map((question, index) => ({
                ...question,
                displayNumber: index + 1  // 按位置重新编号
            }))
        };
        
        console.log('开始发布问卷...', sortedSurvey);
        
        const sessionId = localStorage.getItem('session_id');
        
        const response = await fetch('/api/save-survey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                survey: sortedSurvey,
                session_id: sessionId
            })
        });
        
        console.log('收到响应，状态码:', response.status, response.statusText);
        
        // 检查响应状态
        if (!response.ok) {
            let errorMessage = '发布失败';
            try {
                const errorData = await response.json();
                errorMessage = errorData.message || errorData.detail || `HTTP错误 ${response.status}`;
            } catch (e) {
                errorMessage = `HTTP错误 ${response.status}: ${response.statusText}`;
            }
            alert('发布问卷失败: ' + errorMessage);
            console.error('发布问卷失败:', errorMessage);
            return;
        }
        
        const data = await response.json();
        console.log('响应数据:', data);
        
        if (data.success !== false && data.survey_id) {
            showShareLink(data.survey_id);
        } else {
            alert('发布问卷失败: ' + (data.message || '未知错误'));
        }
    } catch (error) {
        console.error('发布问卷错误:', error);
        alert('发布问卷失败: ' + (error.message || '网络错误，请检查网络连接或稍后重试'));
    }
}

// showShareLink 和 copyShareLink 函数已在上面定义，这里不需要重复定义

// 页面加载完成后绑定事件
document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateSurvey);
    }
    
    // 支持回车键生成
    const surveyPrompt = document.getElementById('surveyPrompt');
    if (surveyPrompt) {
        surveyPrompt.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                generateBtn.click();
            }
        });
    }
});