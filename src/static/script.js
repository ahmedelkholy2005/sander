let uploadedEmails = [];
let currentCampaignId = null;

// تحميل ملف Excel
async function uploadExcel() {
    const fileInput = document.getElementById('excelFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showAlert('يرجى اختيار ملف Excel', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showLoading(true);
        const response = await fetch('/api/upload-excel', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            uploadedEmails = result.emails;
            displayEmails(result.emails);
            document.getElementById('sendBtn').disabled = false;
            showAlert(`تم تحميل ${result.count} إيميل بنجاح`, 'success');
        } else {
            showAlert(result.error, 'danger');
        }
    } catch (error) {
        showAlert('خطأ في تحميل الملف: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

// عرض قائمة الإيميلات
function displayEmails(emails) {
    const emailListCard = document.getElementById('emailListCard');
    const emailList = document.getElementById('emailList');
    const emailCount = document.getElementById('emailCount');
    
    emailCount.textContent = emails.length;
    emailList.innerHTML = '';
    
    emails.forEach((email, index) => {
        const emailItem = document.createElement('div');
        emailItem.className = 'email-item';
        emailItem.innerHTML = `<small>${index + 1}.</small> ${email}`;
        emailList.appendChild(emailItem);
    });
    
    emailListCard.style.display = 'block';
}

// إرسال الإيميلات
document.getElementById('emailForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (uploadedEmails.length === 0) {
        showAlert('يرجى تحميل ملف الإيميلات أولاً', 'warning');
        return;
    }
    
    const formData = {
        sender_name: document.getElementById('senderName').value,
        sender_email: document.getElementById('senderEmail').value,
        subject: document.getElementById('subject').value,
        message: document.getElementById('message').value,
        emails: uploadedEmails,
        smtp_password: document.getElementById('smtpPassword').value
    };
    
    try {
        document.getElementById('sendingProgress').style.display = 'block';
        document.getElementById('sendBtn').disabled = true;
        
        const response = await fetch('/api/send-campaign', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentCampaignId = result.campaign_id;
            showAlert('تم بدء إرسال الإيميلات بنجاح', 'success');
            
            // بدء مراقبة التقدم
            setTimeout(() => {
                monitorProgress(result.campaign_id);
            }, 2000);
        } else {
            showAlert(result.error, 'danger');
            document.getElementById('sendBtn').disabled = false;
        }
    } catch (error) {
        showAlert('خطأ في إرسال الإيميلات: ' + error.message, 'danger');
        document.getElementById('sendBtn').disabled = false;
    } finally {
        document.getElementById('sendingProgress').style.display = 'none';
    }
});

// مراقبة تقدم الإرسال
async function monitorProgress(campaignId) {
    try {
        const response = await fetch(`/api/campaign/${campaignId}/stats`);
        const result = await response.json();
        
        // عرض الإحصائيات
        displayStats(result);
        
        // إذا لم ينته الإرسال بعد، استمر في المراقبة
        if (result.stats.sent + result.stats.failed < result.stats.total) {
            setTimeout(() => monitorProgress(campaignId), 3000);
        } else {
            document.getElementById('sendBtn').disabled = false;
            showAlert('تم الانتهاء من إرسال جميع الإيميلات', 'info');
        }
    } catch (error) {
        console.error('خطأ في مراقبة التقدم:', error);
    }
}

// عرض الإحصائيات
function displayStats(data) {
    const statsContainer = document.getElementById('statsContainer');
    const stats = data.stats;
    
    statsContainer.innerHTML = `
        <div class="col-md-3">
            <div class="stats-card total">
                <h3>${stats.total}</h3>
                <p><i class="fas fa-envelope"></i> إجمالي الإيميلات</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card sent">
                <h3>${stats.sent}</h3>
                <p><i class="fas fa-check"></i> تم الإرسال</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card opened">
                <h3>${stats.opened}</h3>
                <p><i class="fas fa-eye"></i> تم الفتح</p>
            </div>
        </div>
        <div class="col-md-3">
            <div class="stats-card failed">
                <h3>${stats.failed}</h3>
                <p><i class="fas fa-times"></i> فشل الإرسال</p>
            </div>
        </div>
        
        <div class="col-12 mt-4">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-chart-pie"></i> معدل الفتح: ${stats.open_rate.toFixed(1)}%
                </div>
                <div class="card-body">
                    <div class="progress mb-3">
                        <div class="progress-bar bg-success" style="width: ${(stats.sent/stats.total)*100}%"></div>
                        <div class="progress-bar bg-info" style="width: ${(stats.opened/stats.total)*100}%"></div>
                        <div class="progress-bar bg-danger" style="width: ${(stats.failed/stats.total)*100}%"></div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-4">
                            <button class="btn btn-success w-100" onclick="exportEmails(${data.campaign.id}, 'sent')">
                                <i class="fas fa-download"></i> تصدير المرسلة
                            </button>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-info w-100" onclick="exportEmails(${data.campaign.id}, 'opened')">
                                <i class="fas fa-download"></i> تصدير المفتوحة
                            </button>
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-danger w-100" onclick="exportEmails(${data.campaign.id}, 'failed')">
                                <i class="fas fa-download"></i> تصدير الفاشلة
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-12 mt-4">
            <div class="card">
                <div class="card-header">
                    <i class="fas fa-list"></i> تفاصيل الإيميلات
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>الإيميل</th>
                                    <th>الحالة</th>
                                    <th>تاريخ الإرسال</th>
                                    <th>تاريخ الفتح</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.emails.map(email => `
                                    <tr>
                                        <td>${email.recipient_email}</td>
                                        <td>
                                            ${getStatusBadge(email.status, email.is_opened)}
                                        </td>
                                        <td>${email.sent_at ? new Date(email.sent_at).toLocaleString('ar-SA') : '-'}</td>
                                        <td>${email.opened_at ? new Date(email.opened_at).toLocaleString('ar-SA') : '-'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// الحصول على شارة الحالة
function getStatusBadge(status, isOpened) {
    if (status === 'sent' && isOpened) {
        return '<span class="badge bg-info">تم الفتح</span>';
    } else if (status === 'sent') {
        return '<span class="badge bg-success">تم الإرسال</span>';
    } else if (status === 'failed') {
        return '<span class="badge bg-danger">فشل</span>';
    } else {
        return '<span class="badge bg-warning">في الانتظار</span>';
    }
}

// تصدير الإيميلات
async function exportEmails(campaignId, status) {
    try {
        const response = await fetch(`/api/campaign/${campaignId}/export/${status}`);
        const result = await response.json();
        
        if (result.emails && result.emails.length > 0) {
            // إنشاء ملف CSV
            const csvContent = "data:text/csv;charset=utf-8," + 
                "الإيميل\\n" + 
                result.emails.join("\\n");
            
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `emails_${status}_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            showAlert(`تم تصدير ${result.count} إيميل`, 'success');
        } else {
            showAlert('لا توجد إيميلات لتصديرها', 'warning');
        }
    } catch (error) {
        showAlert('خطأ في تصدير الإيميلات: ' + error.message, 'danger');
    }
}

// تحميل الحملات السابقة
async function loadCampaigns() {
    try {
        const response = await fetch('/api/campaigns');
        const campaigns = await response.json();
        
        const campaignsList = document.getElementById('campaignsList');
        
        if (campaigns.length === 0) {
            campaignsList.innerHTML = '<div class="alert alert-info">لا توجد حملات سابقة</div>';
            return;
        }
        
        campaignsList.innerHTML = `
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>التاريخ</th>
                            <th>اسم المرسل</th>
                            <th>الموضوع</th>
                            <th>الإجراءات</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${campaigns.map(campaign => `
                            <tr>
                                <td>${new Date(campaign.created_at).toLocaleString('ar-SA')}</td>
                                <td>${campaign.sender_name}</td>
                                <td>${campaign.subject}</td>
                                <td>
                                    <button class="btn btn-sm btn-primary" onclick="viewCampaignStats(${campaign.id})">
                                        <i class="fas fa-chart-bar"></i> عرض الإحصائيات
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        document.getElementById('campaignsList').innerHTML = 
            '<div class="alert alert-danger">خطأ في تحميل الحملات: ' + error.message + '</div>';
    }
}

// عرض إحصائيات حملة معينة
async function viewCampaignStats(campaignId) {
    try {
        const response = await fetch(`/api/campaign/${campaignId}/stats`);
        const result = await response.json();
        
        displayStats(result);
        
        // التبديل إلى تبويب الإحصائيات
        const statsTab = new bootstrap.Tab(document.getElementById('stats-tab'));
        statsTab.show();
    } catch (error) {
        showAlert('خطأ في تحميل إحصائيات الحملة: ' + error.message, 'danger');
    }
}

// عرض رسالة تنبيه
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.insertBefore(alertDiv, document.body.firstChild);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// عرض/إخفاء مؤشر التحميل
function showLoading(show) {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(element => {
        element.style.display = show ? 'block' : 'none';
    });
}

// تحميل الحملات عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    loadCampaigns();
    
    // إضافة مستمع لتبويب الحملات
    document.getElementById('campaigns-tab').addEventListener('shown.bs.tab', function() {
        loadCampaigns();
    });
});

