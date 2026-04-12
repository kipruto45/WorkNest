<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><?php echo $pageTitle ?? 'WorkNest'; ?></title>
  <link rel="stylesheet" href="/assets/css/variables.css">
  <link rel="stylesheet" href="/assets/css/reset.css">
  <link rel="stylesheet" href="/assets/css/utilities.css">
  <link rel="stylesheet" href="/assets/css/base.css">
  <link rel="stylesheet" href="/assets/css/sidebar.css">
  <link rel="stylesheet" href="/assets/css/topbar.css">
  <link rel="stylesheet" href="/assets/css/cards.css">
  <link rel="stylesheet" href="/assets/css/buttons.css">
  <link rel="stylesheet" href="/assets/css/badges.css">
  <link rel="stylesheet" href="/assets/css/dropdowns.css">
  <link rel="stylesheet" href="/assets/css/animations.css">
  <link rel="stylesheet" href="/assets/css/modals.css">
  <link rel="stylesheet" href="/assets/css/forms.css">
  <?php if (isset($extraCss)): ?>
    <?php foreach ($extraCss as $css): ?>
      <link rel="stylesheet" href="<?php echo $css; ?>">
    <?php endforeach; ?>
  <?php endif; ?>
</head>
<body>
  <?php echo $content; ?>
  
  <script src="/assets/js/app.js"></script>
  <script>
    // Global configuration
    window.API_BASE = '/api';
    window.CSRF_TOKEN = '<?php echo \Core\CSRF::token(); ?>';
    
    // Current user data
    window.currentUser = <?php echo json_encode($currentUser ?? null); ?>;
  </script>
  <?php if (isset($extraJs)): ?>
    <?php foreach ($extraJs as $js): ?>
      <script src="<?php echo $js; ?>"></script>
    <?php endforeach; ?>
  <?php endif; ?>
</body>
</html>