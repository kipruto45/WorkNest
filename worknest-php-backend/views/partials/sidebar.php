<aside class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-logo">
      <div class="sidebar-logo-icon">W</div>
      <span class="sidebar-logo-text">WorkNest</span>
    </div>
    <button class="sidebar-toggle" onclick="toggleSidebar()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
    </button>
  </div>
  
  <nav class="sidebar-nav">
    <div class="sidebar-section">
      <div class="sidebar-section-title">Main</div>
      <a href="/dashboard" class="sidebar-nav-item <?php echo $page === 'dashboard' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
        <span class="sidebar-nav-text">Dashboard</span>
      </a>
      <a href="/my-tasks" class="sidebar-nav-item <?php echo $page === 'my-tasks' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
        <span class="sidebar-nav-text">My Tasks</span>
        <?php if ($myTaskCount > 0): ?>
          <span class="sidebar-nav-badge"><?php echo $myTaskCount; ?></span>
        <?php endif; ?>
      </a>
      <a href="/teams" class="sidebar-nav-item <?php echo $page === 'teams' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
        <span class="sidebar-nav-text">Teams</span>
      </a>
      <a href="/files" class="sidebar-nav-item <?php echo $page === 'files' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
        <span class="sidebar-nav-text">Files</span>
      </a>
    </div>
    
    <div class="sidebar-section">
      <div class="sidebar-section-title">Tools</div>
      <a href="/board" class="sidebar-nav-item <?php echo $page === 'board' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
        <span class="sidebar-nav-text">Board</span>
      </a>
      <a href="/activity" class="sidebar-nav-item <?php echo $page === 'activity' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        <span class="sidebar-nav-text">Activity</span>
      </a>
      <a href="/reports" class="sidebar-nav-item <?php echo $page === 'reports' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
        <span class="sidebar-nav-text">Reports</span>
      </a>
    </div>
    
    <div class="sidebar-section">
      <div class="sidebar-section-title">Settings</div>
      <a href="/notifications" class="sidebar-nav-item <?php echo $page === 'notifications' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
        <span class="sidebar-nav-text">Notifications</span>
        <?php if ($unreadNotificationCount > 0): ?>
          <span class="sidebar-nav-badge"><?php echo $unreadNotificationCount; ?></span>
        <?php endif; ?>
      </a>
      <a href="/settings" class="sidebar-nav-item <?php echo $page === 'settings' ? 'active' : ''; ?>">
        <svg class="sidebar-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
        <span class="sidebar-nav-text">Settings</span>
      </a>
    </div>
  </nav>
  
  <div class="sidebar-footer">
    <div class="sidebar-team-selector" onclick="showTeamSelector()">
      <?php if (isset($currentTeam) && $currentTeam): ?>
        <div class="sidebar-team-avatar"><?php echo strtoupper(substr($currentTeam['name'], 0, 2)); ?></div>
        <div class="sidebar-team-info">
          <div class="sidebar-team-name"><?php echo htmlspecialchars($currentTeam['name']); ?></div>
          <div class="sidebar-team-role"><?php echo htmlspecialchars($currentUser['role'] ?? 'Member'); ?></div>
        </div>
      <?php else: ?>
        <div class="sidebar-team-avatar">?</div>
        <div class="sidebar-team-info">
          <div class="sidebar-team-name">Select Team</div>
          <div class="sidebar-team-role">--</div>
        </div>
      <?php endif; ?>
      <svg class="sidebar-team-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
    </div>
  </div>
</aside>

<script>
function toggleSidebar() {
  document.querySelector('.sidebar').classList.toggle('collapsed');
  localStorage.setItem('sidebar-collapsed', document.querySelector('.sidebar').classList.contains('collapsed'));
}

// Restore sidebar state
document.addEventListener('DOMContentLoaded', function() {
  if (localStorage.getItem('sidebar-collapsed') === 'true') {
    document.querySelector('.sidebar').classList.add('collapsed');
  }
});
</script>