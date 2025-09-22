frappe.pages['assistant-admin'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Assistant Admin',
        single_column: true
    });

    // Add custom styles
    const styles = `
        <style>
            .assistant-admin-container {
                max-width: 1400px;
                margin: 0 auto;
            }
            .status-card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                border: 1px solid #e0e0e0;
            }
            .status-card.enabled {
                border-left: 4px solid #28a745;
            }
            .status-card.disabled {
                border-left: 4px solid #dc3545;
            }
            .status-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .status-title {
                font-size: 16px;
                font-weight: 600;
                color: #2c3e50;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .status-icon {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }
            .status-icon.green {
                background: #28a745;
                box-shadow: 0 0 0 3px rgba(40, 167, 69, 0.2);
            }
            .status-icon.red {
                background: #dc3545;
                box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.2);
            }
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .info-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 8px;
                padding: 20px;
                color: white;
            }
            .info-card h3 {
                margin: 0 0 15px 0;
                font-size: 14px;
                opacity: 0.9;
                font-weight: 500;
            }
            .info-stat {
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .info-detail {
                font-size: 13px;
                opacity: 0.9;
            }
            .tool-registry-container {
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                margin-bottom: 20px;
            }
            .tool-registry-header {
                background: #f8f9fa;
                padding: 15px 20px;
                border-bottom: 1px solid #e0e0e0;
                font-weight: 600;
                color: #2c3e50;
            }
            .tool-registry-body {
                max-height: 400px;
                overflow-y: auto;
            }
            .tool-item {
                padding: 12px 20px;
                border-bottom: 1px solid #f0f0f0;
                transition: background 0.2s;
            }
            .tool-item:hover {
                background: #f8f9fa;
            }
            .tool-name {
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 4px;
            }
            .tool-meta {
                display: flex;
                gap: 15px;
                align-items: center;
                margin-bottom: 4px;
            }
            .tool-category {
                display: inline-block;
                padding: 2px 8px;
                background: #e9ecef;
                border-radius: 12px;
                font-size: 11px;
                color: #495057;
                font-weight: 500;
            }
            .tool-description {
                font-size: 13px;
                color: #6c757d;
                line-height: 1.4;
            }
            .tool-status {
                width: 6px;
                height: 6px;
                border-radius: 50%;
                display: inline-block;
            }
            .tool-status.active {
                background: #28a745;
            }
            .tool-status.inactive {
                background: #dee2e6;
            }
            .activity-table {
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            }
            .activity-header {
                background: #f8f9fa;
                padding: 15px 20px;
                border-bottom: 1px solid #e0e0e0;
                font-weight: 600;
                color: #2c3e50;
            }
        </style>
    `;

    page.main.html(styles + `
        <div class="assistant-admin-container">
            <!-- Status Card -->
            <div id="status-card" class="status-card">
                <div class="status-header">
                    <div class="status-title">
                        <span id="status-icon" class="status-icon"></span>
                        <span id="status-text">Loading...</span>
                    </div>
                    <button class="btn btn-sm btn-default" id="open-settings">
                        <i class="fa fa-cog"></i> Settings
                    </button>
                </div>
            </div>

            <!-- SSE Bridge Status Card -->
            <div id="sse-bridge-card" class="status-card">
                <div class="status-header">
                    <div class="status-title">
                        <span id="sse-status-icon" class="status-icon"></span>
                        <span id="sse-status-text">
                            <i class="fa fa-broadcast-tower"></i> SSE Bridge - Loading...
                        </span>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-success" id="start-sse-bridge" style="display:none;">
                            <i class="fa fa-play"></i> Start
                        </button>
                        <button class="btn btn-warning" id="stop-sse-bridge" style="display:none;">
                            <i class="fa fa-stop"></i> Stop
                        </button>
                        <button class="btn btn-info" id="check-sse-status">
                            <i class="fa fa-refresh"></i> Status
                        </button>
                    </div>
                </div>
                <div id="sse-details" style="display:none; margin-top: 15px;">
                    <div class="row">
                        <div class="col-md-3">
                            <strong>Port:</strong> <span id="sse-port">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Host:</strong> <span id="sse-host">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Process ID:</strong> <span id="sse-pid">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Connections:</strong> <span id="sse-connections">-</span>
                        </div>
                    </div>
                    <div class="row" style="margin-top: 10px;">
                        <div class="col-md-3">
                            <strong>Messages:</strong> <span id="sse-messages">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Storage:</strong> <span id="sse-storage">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Enabled:</strong> <span id="sse-enabled">-</span>
                        </div>
                        <div class="col-md-3">
                            <strong>Debug:</strong> <span id="sse-debug">-</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Info Grid -->
            <div class="info-grid">
                <div class="info-card">
                    <h3>PLUGINS</h3>
                    <div id="plugin-stats">
                        <div class="info-stat">-</div>
                        <div class="info-detail">Loading...</div>
                    </div>
                </div>
                <div class="info-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                    <h3>TOOLS</h3>
                    <div id="tool-stats">
                        <div class="info-stat">-</div>
                        <div class="info-detail">Loading...</div>
                    </div>
                </div>
                <div class="info-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                    <h3>TODAY'S ACTIVITY</h3>
                    <div id="activity-stats">
                        <div class="info-stat">-</div>
                        <div class="info-detail">Tool executions today</div>
                    </div>
                </div>
            </div>

            <!-- Tool Registry -->
            <div class="tool-registry-container">
                <div class="tool-registry-header">
                    <i class="fa fa-tools"></i> Tool Registry
                </div>
                <div class="tool-registry-body" id="tool-registry">
                    <div style="padding: 20px; text-align: center;">
                        <i class="fa fa-spinner fa-spin"></i> Loading tools...
                    </div>
                </div>
            </div>

            <!-- Recent Activity -->
            <div class="activity-table" style="margin-bottom: 20px;">
                <div class="activity-header">
                    <i class="fa fa-history"></i> Recent Activity
                </div>
                <div id="recent-activity" style="padding: 20px;">
                    <div style="text-align: center;">
                        <i class="fa fa-spinner fa-spin"></i> Loading activity...
                    </div>
                </div>
            </div>
        </div>
    `);

    // Load assistant status
    function loadAssistantStatus() {
        frappe.call({
            method: "frappe_assistant_core.assistant_core.server.get_server_status",
            callback: function(response) {
                if (response.message) {
                    const status = response.message;
                    const statusCard = $('#status-card');
                    const statusIcon = $('#status-icon');
                    const statusText = $('#status-text');

                    if (status.enabled) {
                        statusCard.removeClass('disabled').addClass('enabled');
                        statusIcon.removeClass('red').addClass('green');
                        statusText.html('Frappe Assistant Core is <strong>enabled</strong>');
                    } else {
                        statusCard.removeClass('enabled').addClass('disabled');
                        statusIcon.removeClass('green').addClass('red');
                        statusText.html('Frappe Assistant Core is <strong>disabled</strong>');
                    }
                }
            },
            error: function() {
                $('#status-text').html('<span class="text-danger">Failed to load status</span>');
            }
        });
    }

    // Load plugin and tool info
    function loadPluginInfo() {
        frappe.call({
            method: "frappe_assistant_core.api.admin_api.get_plugin_stats",
            callback: function(response) {
                if (response.message) {
                    const stats = response.message;
                    $('#plugin-stats').html(`
                        <div class="info-stat">${stats.enabled_count || 0}</div>
                        <div class="info-detail">${stats.enabled_count} enabled / ${stats.total_count} total</div>
                    `);

                    frappe.call({
                        method: "frappe_assistant_core.api.admin_api.get_tool_stats",
                        callback: function(toolResponse) {
                            const toolStats = toolResponse.message || {};
                            $('#tool-stats').html(`
                                <div class="info-stat">${toolStats.total_tools || 0}</div>
                                <div class="info-detail">Available tools</div>
                            `);
                        }
                    });
                }
            }
        });

        // Load activity stats
        frappe.call({
            method: "frappe_assistant_core.api.assistant_api.get_usage_statistics",
            callback: function(response) {
                if (response.message && response.message.success) {
                    const stats = response.message.data;
                    // Use audit_logs.today instead of connections.today for more meaningful metric
                    $('#activity-stats').html(`
                        <div class="info-stat">${stats.audit_logs.today || 0}</div>
                        <div class="info-detail">Tool executions today</div>
                    `);
                }
            }
        });
    }

    // Load tool registry
    function loadToolRegistry() {
        frappe.call({
            method: "frappe_assistant_core.api.admin_api.get_tool_registry",
            callback: function(response) {
                if (response.message && response.message.tools) {
                    const tools = response.message.tools;
                    if (tools.length > 0) {
                        const toolsHtml = tools.map(tool => `
                            <div class="tool-item">
                                <div class="tool-name">${tool.name}</div>
                                <div class="tool-meta">
                                    <span class="tool-category">${tool.category || 'General'}</span>
                                    <span class="tool-status ${tool.enabled ? 'active' : 'inactive'}"></span>
                                    <span style="font-size: 11px; color: ${tool.enabled ? '#28a745' : '#6c757d'};">
                                        ${tool.enabled ? 'Active' : 'Inactive'}
                                    </span>
                                </div>
                                <div class="tool-description">${tool.description || 'No description available'}</div>
                            </div>
                        `).join('');
                        $('#tool-registry').html(toolsHtml);
                    } else {
                        $('#tool-registry').html('<div style="padding: 20px; text-align: center; color: #6c757d;">No tools available</div>');
                    }
                }
            },
            error: function() {
                $('#tool-registry').html('<div style="padding: 20px; text-align: center; color: #dc3545;">Failed to load tools</div>');
            }
        });
    }

    // Load recent activity
    function loadRecentActivity() {
        frappe.call({
            method: "frappe_assistant_core.api.assistant_api.get_usage_statistics",
            callback: function(response) {
                if (response.message && response.message.success) {
                    const activities = response.message.data.recent_activity || [];
                    if (activities.length > 0) {
                        const tableHtml = `
                            <table class="table table-sm" style="margin: 0;">
                                <thead style="background: #f8f9fa;">
                                    <tr>
                                        <th style="border-top: none;">Action</th>
                                        <th style="border-top: none;">Tool</th>
                                        <th style="border-top: none;">User</th>
                                        <th style="border-top: none;">Status</th>
                                        <th style="border-top: none;">Time</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${activities.slice(0, 5).map(a => `
                                        <tr>
                                            <td>${a.action}</td>
                                            <td>${a.tool_name || '-'}</td>
                                            <td>${a.user}</td>
                                            <td>
                                                <span class="badge badge-${a.status === 'Success' ? 'success' : 'danger'}" style="font-size: 11px;">
                                                    ${a.status}
                                                </span>
                                            </td>
                                            <td class="text-muted" style="font-size: 13px;">
                                                ${frappe.datetime.str_to_user(a.timestamp)}
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                        $('#recent-activity').html(tableHtml);
                    } else {
                        $('#recent-activity').html('<div style="text-align: center; color: #6c757d;">No recent activity</div>');
                    }
                }
            },
            error: function() {
                $('#recent-activity').html('<div style="text-align: center; color: #dc3545;">Failed to load activity</div>');
            }
        });
    }

    // Load SSE Bridge status
    function loadSSEBridgeStatus() {
        // First check if SSE bridge is enabled
        frappe.call({
            method: "frappe.client.get",
            args: {
                doctype: "Assistant Core Settings"
            },
            callback: function(response) {
                if (response.message) {
                    // Check if SSE bridge is enabled first
                    if (!response.message.sse_bridge_enabled) {
                        updateSSEBridgeUI({
                            success: true,
                            status: "disabled",
                            message: "SSE bridge is disabled in settings",
                            enabled: false,
                            port: response.message.sse_bridge_port || 8080,
                            host: response.message.sse_bridge_host || "0.0.0.0"
                        });
                        return;
                    }

                    // SSE bridge is enabled, get actual status
                    frappe.call({
                        method: "frappe_assistant_core.assistant_core.doctype.assistant_core_settings.assistant_core_settings.api_get_sse_bridge_status",
                        callback: function(statusResponse) {
                            updateSSEBridgeUI(statusResponse.message);
                        },
                        error: function() {
                            updateSSEBridgeUI({
                                success: false,
                                status: "error",
                                message: "Failed to get SSE bridge status",
                                enabled: response.message.sse_bridge_enabled
                            });
                        }
                    });
                }
            },
            error: function() {
                updateSSEBridgeUI({
                    success: false,
                    status: "error",
                    message: "Failed to load Assistant Core Settings",
                    enabled: false
                });
            }
        });
    }

    // Update SSE Bridge UI
    function updateSSEBridgeUI(status) {
        const card = $('#sse-bridge-card');
        const statusIcon = $('#sse-status-icon');
        const statusText = $('#sse-status-text');
        const details = $('#sse-details');
        const startBtn = $('#start-sse-bridge');
        const stopBtn = $('#stop-sse-bridge');

        // Update status display
        statusText.html(`<i class="fa fa-broadcast-tower"></i> SSE Bridge - ${status.message || status.status}`);

        if (status.status === 'running') {
            card.removeClass('disabled').addClass('enabled');
            statusIcon.removeClass('red').addClass('green');
            startBtn.hide();
            stopBtn.show();
            details.show();

            // Update details
            $('#sse-port').text(status.port || '-');
            $('#sse-host').text(status.host || '-');
            $('#sse-pid').text(status.process_id || '-');
            $('#sse-connections').text(status.server_info?.active_connections || '0');
            $('#sse-messages').text(status.server_info?.messages_sent || '0');
            $('#sse-storage').text(status.server_info?.storage_backend || 'memory');
            $('#sse-enabled').html(status.enabled ? '<span class="text-success">Yes</span>' : '<span class="text-danger">No</span>');
            $('#sse-debug').html('<span class="text-muted">N/A</span>');

        } else if (status.status === 'disabled') {
            card.removeClass('enabled').addClass('disabled');
            statusIcon.removeClass('green').addClass('red');
            startBtn.hide();
            stopBtn.hide();
            details.show();

            // Show configuration info even when disabled
            $('#sse-port').text(status.port || '-');
            $('#sse-host').text(status.host || '-');
            $('#sse-pid').text('N/A (Disabled)');
            $('#sse-connections').text('N/A');
            $('#sse-messages').text('N/A');
            $('#sse-storage').text('N/A');
            $('#sse-enabled').html('<span class="text-warning">Disabled - <a href="#Form/Assistant Core Settings">Enable in Settings</a></span>');
            $('#sse-debug').text('N/A');

        } else if (status.status === 'stopped' || status.status === 'error') {
            card.removeClass('enabled').addClass('disabled');
            statusIcon.removeClass('green').addClass('red');
            startBtn.show();
            stopBtn.hide();
            details.hide();

        } else if (status.status === 'starting') {
            card.removeClass('disabled enabled');
            statusIcon.removeClass('green red');
            startBtn.hide();
            stopBtn.show();
            details.hide();
        }

        // Always show enabled status if available
        if (status.enabled !== undefined) {
            $('#sse-enabled').html(status.enabled ? '<span class="text-success">Yes</span>' : '<span class="text-danger">No</span>');
        }
    }

    // SSE Bridge control functions
    function startSSEBridge() {
        startBtn = $('#start-sse-bridge');
        startBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Starting...');

        frappe.call({
            method: "frappe_assistant_core.assistant_core.doctype.assistant_core_settings.assistant_core_settings.api_start_sse_bridge",
            callback: function(response) {
                if (response.message && response.message.success) {
                    frappe.show_alert({
                        message: 'SSE Bridge started successfully',
                        indicator: 'green'
                    });
                    setTimeout(loadSSEBridgeStatus, 2000); // Reload status after 2 seconds
                } else {
                    frappe.show_alert({
                        message: 'Failed to start SSE Bridge: ' + (response.message?.message || 'Unknown error'),
                        indicator: 'red'
                    });
                }
            },
            error: function(xhr) {
                frappe.show_alert({
                    message: 'Error starting SSE Bridge: ' + (xhr.responseJSON?.message || 'Unknown error'),
                    indicator: 'red'
                });
            },
            always: function() {
                startBtn.prop('disabled', false).html('<i class="fa fa-play"></i> Start');
                loadSSEBridgeStatus();
            }
        });
    }

    function stopSSEBridge() {
        stopBtn = $('#stop-sse-bridge');
        stopBtn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Stopping...');

        frappe.call({
            method: "frappe_assistant_core.assistant_core.doctype.assistant_core_settings.assistant_core_settings.api_stop_sse_bridge",
            callback: function(response) {
                if (response.message && response.message.success) {
                    frappe.show_alert({
                        message: 'SSE Bridge stopped successfully',
                        indicator: 'orange'
                    });
                } else {
                    frappe.show_alert({
                        message: 'Failed to stop SSE Bridge: ' + (response.message?.message || 'Unknown error'),
                        indicator: 'red'
                    });
                }
            },
            error: function(xhr) {
                frappe.show_alert({
                    message: 'Error stopping SSE Bridge: ' + (xhr.responseJSON?.message || 'Unknown error'),
                    indicator: 'red'
                });
            },
            always: function() {
                stopBtn.prop('disabled', false).html('<i class="fa fa-stop"></i> Stop');
                loadSSEBridgeStatus();
            }
        });
    }

    // Event handlers
    $('#open-settings').on('click', function() {
        frappe.set_route('Form', 'Assistant Core Settings');
    });

    $('#start-sse-bridge').on('click', startSSEBridge);
    $('#stop-sse-bridge').on('click', stopSSEBridge);
    $('#check-sse-status').on('click', loadSSEBridgeStatus);

    // Initial load
    loadAssistantStatus();
    loadPluginInfo();
    loadToolRegistry();
    loadRecentActivity();
    loadSSEBridgeStatus(); // Load SSE bridge status

    // Refresh every 30 seconds
    setInterval(function() {
        loadAssistantStatus();
        loadRecentActivity();
        loadSSEBridgeStatus(); // Also refresh SSE bridge status
    }, 30000);
};