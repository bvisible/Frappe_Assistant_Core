// Copyright (c) 2025, Paul Clinton and contributors
// For license information, please see license.txt

frappe.ui.form.on("Assistant Core Settings", {
    refresh(frm) {
        // Load plugin status in HTML field
        frm.call('get_plugin_status').then(response => {
            if (response.message && response.message.success) {
                frm.set_df_property('plugin_status_html', 'options', response.message.html);
                frm.refresh_field('plugin_status_html');
            }
        });
        
        // Load SSE bridge status
        frm.call('get_sse_bridge_status').then(response => {
            if (response.message) {
                frm.events.update_sse_bridge_status(frm, response.message);
            }
        });
        
        // Add custom buttons
        frm.add_custom_button(__('Refresh Plugin System'), function() {
            frappe.call({
                method: 'refresh_plugins',
                doc: frm.doc,
                callback: function(response) {
                    if (!response.exc) {
                        frm.reload_doc();
                    }
                }
            });
        }, __('Actions'));
        
        // SSE Bridge control buttons
        if (frm.doc.sse_bridge_enabled) {
            frm.add_custom_button(__('Start SSE Bridge'), function() {
                frappe.call({
                    method: 'start_sse_bridge',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Starting SSE Bridge...'),
                    callback: function(response) {
                        if (!response.exc) {
                            frappe.show_alert({
                                message: __('SSE Bridge started successfully'),
                                indicator: 'green'
                            });
                            setTimeout(() => frm.reload_doc(), 2000);
                        }
                    }
                });
            }, __('SSE Bridge'));
            
            frm.add_custom_button(__('Stop SSE Bridge'), function() {
                frappe.confirm(
                    __('Are you sure you want to stop the SSE Bridge?'),
                    function() {
                        frappe.call({
                            method: 'stop_sse_bridge',
                            doc: frm.doc,
                            freeze: true,
                            freeze_message: __('Stopping SSE Bridge...'),
                            callback: function(response) {
                                if (!response.exc) {
                                    frappe.show_alert({
                                        message: __('SSE Bridge stopped successfully'),
                                        indicator: 'orange'
                                    });
                                    setTimeout(() => frm.reload_doc(), 1000);
                                }
                            }
                        });
                    }
                );
            }, __('SSE Bridge'));
            
            frm.add_custom_button(__('Check SSE Bridge Status'), function() {
                frm.call('get_sse_bridge_status').then(response => {
                    if (response.message) {
                        frm.events.update_sse_bridge_status(frm, response.message);
                        frappe.show_alert({
                            message: response.message.message,
                            indicator: response.message.status === 'running' ? 'green' : 'orange'
                        });
                    }
                });
            }, __('SSE Bridge'));
        }
    },
    
    update_sse_bridge_status: function(frm, status) {
        const statusColors = {
            'running': 'success',
            'starting': 'warning', 
            'stopped': 'secondary',
            'error': 'danger'
        };
        
        const statusIcons = {
            'running': 'fa-check-circle',
            'starting': 'fa-spinner fa-spin',
            'stopped': 'fa-stop-circle',
            'error': 'fa-exclamation-circle'
        };
        
        const color = statusColors[status.status] || 'secondary';
        const icon = statusIcons[status.status] || 'fa-question-circle';
        
        let html = `
            <div class="card">
                <div class="card-header">
                    <h6><i class="fa fa-broadcast-tower text-primary"></i> SSE Bridge Status</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="d-flex align-items-center mb-3">
                                <i class="fa ${icon} text-${color} mr-2" style="font-size: 1.2em;"></i>
                                <span class="badge badge-${color}">${status.status.toUpperCase()}</span>
                            </div>
                            <p class="text-muted mb-2">${status.message}</p>
                            <div class="small text-info">
                                <div><i class="fa fa-server"></i> <strong>Host:</strong> ${status.host}</div>
                                <div><i class="fa fa-network-port"></i> <strong>Port:</strong> ${status.port}</div>
                                <div><i class="fa fa-toggle-${status.enabled ? 'on' : 'off'}"></i> <strong>Enabled:</strong> ${status.enabled ? 'Yes' : 'No'}</div>
                                ${status.process_id ? `<div><i class="fa fa-hashtag"></i> <strong>Process ID:</strong> ${status.process_id}</div>` : ''}
                            </div>
                        </div>
                        <div class="col-md-6">
                            ${status.server_info && Object.keys(status.server_info).length > 0 ? `
                                <h6 class="text-muted">Server Information</h6>
                                <div class="small">
                                    ${status.server_info.active_connections ? `<div><i class="fa fa-users"></i> Active Connections: ${status.server_info.active_connections}</div>` : ''}
                                    ${status.server_info.messages_sent ? `<div><i class="fa fa-paper-plane"></i> Messages Sent: ${status.server_info.messages_sent}</div>` : ''}
                                    ${status.server_info.storage_backend ? `<div><i class="fa fa-database"></i> Storage: ${status.server_info.storage_backend}</div>` : ''}
                                </div>
                            ` : '<p class="text-muted small">No server information available</p>'}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        frm.set_df_property('sse_bridge_status_html', 'options', html);
        frm.refresh_field('sse_bridge_status_html');
    }
});
