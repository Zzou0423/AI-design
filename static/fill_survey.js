// 独立填写页面逻辑

let answers = {};

document.addEventListener('DOMContentLoaded', function() {
    const survey = window.surveyData;
    const surveyId = window.surveyId;
    
    displayFillableSurvey(survey);
});

function displayFillableSurvey(survey) {
    let html = '<div class="survey-container-fillable">';
    
    // 标题
    html += `<div class="survey-title">${escapeHtml(survey.title || '问卷')}</div>`;
    
    // 元信息
    if (survey.target_audience || survey.estimated_time) {
        html += '<div class="survey-meta">';
        if (survey.target_audience) html += `目标受众: ${escapeHtml(survey.target_audience)}`;
        if (survey.estimated_time) html += ` | 预计时间: ${escapeHtml(survey.estimated_time)}`;
        html += '</div>';
    }
    
    // 描述
    if (survey.description) {
        html += `<div class="survey-description">${escapeHtml(survey.description)}</div>`;
    }
    
    // 问题
    if (survey.questions && survey.questions.length > 0) {
        survey.questions.forEach((question, index) => {
            html += renderFillableQuestion(question, index);
        });
    }
    
    // 提交按钮
    html += `
        <div class="action-buttons" style="margin-top: 32px; display: flex; gap: 16px; justify-content: center;">
            <button id="submitResponseBtn" class="btn-primary">提交答案</button>
        </div>
    `;
    
    html += '</div>';
    
    document.getElementById('surveyResult').innerHTML = html;
    
    // 绑定交互
    setTimeout(() => {
        document.getElementById('submitResponseBtn')?.addEventListener('click', submitResponse);
        bindQuestionInteractions();
    }, 100);
}

function renderFillableQuestion(question, index) {
    const qid = question.id || index + 1;
    let html = `<div class="question-item" data-question-id="${qid}">`;
    
    // 问题头部
    html += '<div class="question-header">';
    html += `<span class="question-number">问题 ${qid}</span>`;
    html += `<span class="question-type-badge">${escapeHtml(question.type || '问题')}</span>`;
    if (question.required) html += '<span class="required-badge">必填</span>';
    html += '</div>';
    
    // 问题文本
    html += `<div class="question-text-fillable">${escapeHtml(question.text || '')}</div>`;
    
    // 根据问题类型渲染
    // 为矩阵题特殊处理
    if (question.type === '矩阵题') {
        const subQuestions = question.sub_questions || [];
        const brands = question.brands || [];
        const min = question.scale_min || 1;
        const max = question.scale_max || 5;
        const labels = question.scale_labels || {};
        
        html += '<div class="matrix-container">';
        html += '<table class="matrix-table">';
        html += '<thead><tr><th></th>';
        subQuestions.forEach(sq => {
            html += `<th>${escapeHtml(sq)}</th>`;
        });
        html += '</tr></thead>';
        html += '<tbody>';
        brands.forEach((brand, brandIndex) => {
            html += `<tr><td class="brand-name">${escapeHtml(brand)}</td>`;
            subQuestions.forEach((sq, sqIndex) => {
                const cellId = `${qid}_${brandIndex}_${sqIndex}`;
                html += '<td><select class="matrix-select"';
                html += ` data-question-id="${qid}" data-brand-index="${brandIndex}" data-sub-q="${sqIndex}"`;
                html += '><option value="">请选择</option>';
                for (let i = min; i <= max; i++) {
                    const label = labels[i.toString()] || i.toString();
                    html += `<option value="${i}">${i}</option>`;
                }
                html += '</select></td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        html += '</div>';
    }
    // 根据问题类型渲染
    else if (question.type === '单选题' && question.options) {
        html += '<div class="options-container">';
        question.options.forEach((option, optIndex) => {
            const isOther = option.toLowerCase().includes('其他') || option.toLowerCase().includes('other');
            html += `
                <label class="option-item radio-option" ${isOther ? 'style="display: flex; align-items: center; gap: 8px;"' : ''}>
                    <input type="radio" name="q${qid}" value="${escapeHtml(option)}" data-question-id="${qid}" data-question-type="单选题" data-is-other="${isOther}">
                    <span class="option-text">${escapeHtml(option)}</span>
                    ${isOther ? `<input type="text" class="other-input" placeholder="请说明其他..." data-question-id="${qid}" disabled>` : ''}
                </label>
            `;
        });
        html += '</div>';
    }
    else if (question.type === '多选题' && question.options) {
        html += '<div class="options-container">';
        question.options.forEach((option, optIndex) => {
            const isOther = option.toLowerCase().includes('其他') || option.toLowerCase().includes('other');
            html += `
                <label class="option-item checkbox-option" ${isOther ? 'style="display: flex; align-items: center; gap: 8px;"' : ''}>
                    <input type="checkbox" name="q${qid}" value="${escapeHtml(option)}" data-question-id="${qid}" data-question-type="多选题" data-is-other="${isOther}">
                    <span class="option-text">${escapeHtml(option)}</span>
                    ${isOther ? `<input type="text" class="other-input" placeholder="请说明其他..." data-question-id="${qid}" disabled>` : ''}
                </label>
            `;
        });
        html += '</div>';
    }
    else if (question.type === '量表题') {
        const min = question.scale_min || 1;
        const max = question.scale_max || 5;
        const labels = question.scale_labels || {};
        
        html += '<div class="scale-container">';
        html += '<div class="scale-options">';
        for (let i = min; i <= max; i++) {
            const label = labels[i.toString()] || '';
            html += `
                <label class="scale-item">
                    <input type="radio" name="q${qid}" value="${i}" data-question-id="${qid}" data-question-type="量表题">
                    <span class="scale-number">${i}</span>
                    ${label ? `<span class="scale-label">${escapeHtml(label)}</span>` : ''}
                </label>
            `;
        }
        html += '</div>';
        html += '</div>';
    }
    else if (question.type === '矩阵题') {
        const subQuestions = question.sub_questions || [];
        const brands = question.brands || [];
        const min = question.scale_min || 1;
        const max = question.scale_max || 5;
        const labels = question.scale_labels || {};
        
        html += '<div class="matrix-container">';
        html += '<table class="matrix-table">';
        html += '<thead><tr><th></th>';
        subQuestions.forEach(sq => {
            html += `<th>${escapeHtml(sq)}</th>`;
        });
        html += '</tr></thead>';
        html += '<tbody>';
        brands.forEach((brand, brandIndex) => {
            html += `<tr><td class="brand-name">${escapeHtml(brand)}</td>`;
            subQuestions.forEach((sq, sqIndex) => {
                const cellId = `${qid}_${brandIndex}_${sqIndex}`;
                html += '<td><select class="matrix-select"';
                html += ` data-question-id="${qid}" data-brand-index="${brandIndex}" data-sub-q="${sqIndex}"`;
                html += '><option value="">请选择</option>';
                for (let i = min; i <= max; i++) {
                    const label = labels[i.toString()] || i.toString();
                    html += `<option value="${i}">${i}</option>`;
                }
                html += '</select></td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        html += '</div>';
    }
    else if (question.type === '净推荐值（NPS）题' || question.type === 'NPS题') {
        const min = question.scale_min || 0;
        const max = question.scale_max || 10;
        const labels = question.scale_labels || {};
        
        html += '<div class="nps-container">';
        html += '<div class="nps-scale">';
        html += '<div class="nps-labels">';
        if (labels[min]) html += `<span class="nps-label-start">${escapeHtml(labels[min])}</span>`;
        if (labels[max]) html += `<span class="nps-label-end">${escapeHtml(labels[max])}</span>`;
        html += '</div>';
        html += '<div class="nps-options">';
        for (let i = min; i <= max; i++) {
            html += `
                <label class="nps-item">
                    <input type="radio" name="q${qid}" value="${i}" data-question-id="${qid}" data-question-type="NPS题">
                    <span class="nps-number">${i}</span>
                </label>
            `;
        }
        html += '</div>';
        html += '</div>';
        html += '</div>';
    }
    else if (question.type === '开放式问题') {
        html += `
            <div class="open-question-container">
                <textarea 
                    class="open-question-input" 
                    rows="4" 
                    placeholder="请输入您的回答..."
                    data-question-id="${qid}"
                    data-question-type="开放式问题"
                ></textarea>
            </div>
        `;
    }
    
    html += '</div>';
    return html;
}

function bindQuestionInteractions() {
    // 单选和多选
    document.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', function() {
            const qid = this.getAttribute('data-question-id');
            const type = this.getAttribute('data-question-type');
            const isOther = this.getAttribute('data-is-other') === 'true';
            const value = this.value;
            
            // 处理"其他"选项的文本框
            if (isOther) {
                const otherInput = this.parentNode.querySelector('.other-input');
                if (this.checked) {
                    otherInput.disabled = false;
                    otherInput.focus();
                } else {
                    otherInput.disabled = true;
                    otherInput.value = '';
                }
            }
            
            if (type === '单选题') {
                answers[qid] = { type: type, value: value };
            } else if (type === '多选题') {
                if (!answers[qid]) {
                    answers[qid] = { type: type, value: [] };
                }
                const values = answers[qid].value;
                if (this.checked) {
                    if (!values.includes(value)) values.push(value);
                } else {
                    const index = values.indexOf(value);
                    if (index > -1) values.splice(index, 1);
                }
            } else if (type === '量表题') {
                answers[qid] = { type: type, value: parseInt(value) };
            } else if (type === 'NPS题') {
                answers[qid] = { type: type, value: parseInt(value) };
            }
        });
    });
    
    // 处理"其他"输入框
    document.querySelectorAll('.other-input').forEach(input => {
        input.addEventListener('input', function() {
            const qid = this.getAttribute('data-question-id');
            const otherValue = this.value;
            
            if (answers[qid]) {
                // 更新答案，添加"其他"的具体内容
                if (typeof answers[qid].otherText !== 'undefined') {
                    answers[qid].otherText = otherValue;
                } else if (answers[qid].type === '单选题') {
                    answers[qid].otherText = otherValue;
                } else if (answers[qid].type === '多选题' && Array.isArray(answers[qid].value)) {
                    answers[qid].otherText = otherValue;
                }
            }
        });
    });
    
    // 矩阵题
    document.querySelectorAll('.matrix-select').forEach(select => {
        select.addEventListener('change', function() {
            const qid = this.getAttribute('data-question-id');
            const brandIndex = this.getAttribute('data-brand-index');
            const subQ = this.getAttribute('data-sub-q');
            const value = this.value;
            
            if (!answers[qid]) {
                answers[qid] = { type: '矩阵题', value: {} };
            }
            
            if (!answers[qid].value[brandIndex]) {
                answers[qid].value[brandIndex] = {};
            }
            
            answers[qid].value[brandIndex][subQ] = value;
        });
    });
    
    // 开放性问题
    document.querySelectorAll('.open-question-input').forEach(textarea => {
        textarea.addEventListener('input', function() {
            const qid = this.getAttribute('data-question-id');
            answers[qid] = {
                type: '开放式问题',
                value: this.value
            };
        });
    });
}

function submitResponse() {
    const surveyId = window.surveyId;
    const survey = window.surveyData;
    
    // 如果没有user_id，生成一个并保存到sessionStorage
    let userId = sessionStorage.getItem('survey_user_id');
    if (!userId) {
        userId = 'user_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('survey_user_id', userId);
    }
    
    // 验证必填项
    const requiredQuestions = survey.questions.filter(q => q.required);
    const missingRequired = [];
    
    requiredQuestions.forEach(question => {
        const qid = question.id.toString();
        const answer = answers[qid];
        
        if (!answer) {
            missingRequired.push(question.text);
            return;
        }
        
        // 根据题型验证答案完整性
        if (question.type === '矩阵题') {
            // 矩阵题需要检查所有品牌的答案
            const subQuestions = question.sub_questions || [];
            const brands = question.brands || [];
            let hasAnswer = false;
            
            for (let brandIndex = 0; brandIndex < brands.length; brandIndex++) {
                for (let sqIndex = 0; sqIndex < subQuestions.length; sqIndex++) {
                    if (answer.value && answer.value[brandIndex] && answer.value[brandIndex][sqIndex]) {
                        hasAnswer = true;
                        break;
                    }
                }
                if (hasAnswer) break;
            }
            
            if (!hasAnswer) {
                missingRequired.push(question.text);
            }
        } else if (question.type === 'NPS题' || question.type === '净推荐值（NPS）题') {
            if (!answer.value || answer.value === '' || isNaN(answer.value)) {
                missingRequired.push(question.text);
            }
        } else if (Array.isArray(answer.value)) {
            if (answer.value.length === 0) {
                missingRequired.push(question.text);
            }
        } else if (answer.value === '') {
            missingRequired.push(question.text);
        }
    });
    
    if (missingRequired.length > 0) {
        showNotification('请填写以下必填问题：\n' + missingRequired.join('\n'), 'warning');
        return;
    }
    
    const submitBtn = document.getElementById('submitResponseBtn');
    submitBtn.disabled = true;
    submitBtn.textContent = '提交中...';
    
    // 转换答案格式为后端期望的格式（简单键值对）
    const formattedAnswers = {};
    Object.keys(answers).forEach(qid => {
        const answer = answers[qid];
        if (!answer) return;
        
        if (answer.type === '多选题' && Array.isArray(answer.value)) {
            // 多选题：保存为数组，如果有其他文本则合并
            if (answer.otherText && answer.value.includes('其他')) {
                formattedAnswers[qid] = answer.value.map(v => {
                    return v === '其他' ? (v + ': ' + answer.otherText) : v;
                });
            } else {
                formattedAnswers[qid] = answer.value;
            }
        } else if (answer.type === '矩阵题' && answer.value) {
            // 矩阵题：保存为对象
            formattedAnswers[qid] = answer.value;
        } else if (answer.otherText) {
            // 如果有其他选项的文本，合并
            formattedAnswers[qid] = answer.value + (answer.otherText ? ': ' + answer.otherText : '');
        } else {
            // 单选题、量表题、开放式问题、NPS题：直接保存值
            formattedAnswers[qid] = answer.value;
        }
    });
    
    console.log('提交答案:', formattedAnswers);
    
    fetch('/api/submit-response', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            survey_id: surveyId,
            answers: formattedAnswers,
            user_id: userId
        })
    })
    .then(response => response.json())
    .then(data => {
        showNotification('答案已成功提交！感谢您的参与。', 'success');
        // 清空答案
        answers = {};
        // 重置表单
        document.querySelectorAll('input[type="radio"], input[type="checkbox"], textarea').forEach(el => {
            if (el.type === 'checkbox' || el.type === 'radio') {
                el.checked = false;
            } else {
                el.value = '';
            }
        });
        submitBtn.textContent = '已提交';
        submitBtn.disabled = true;
    })
    .catch(error => {
        console.error('提交失败:', error);
        showNotification('提交答案失败：' + error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = '提交答案';
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

