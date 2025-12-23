<#macro registrationLayout bodyClass="" displayInfo=false displayMessage=true displayRequiredFields=false>
<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}">

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>
    <title>${msg("loginTitle",(realm.displayName!''))}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />
    
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Custom Black & White Minimalist Styles -->
    <style>
        /* Global Variables - Black & White Theme */
        :root {
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            --text-primary: rgba(255, 255, 255, 0.95);
            --text-secondary: rgba(255, 255, 255, 0.7);
            --text-muted: rgba(255, 255, 255, 0.5);
            --accent-color: #ffffff;
            --accent-secondary: #e5e5e5;
        }

        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow-x: hidden;
            background: #000000;
            min-height: 100vh;
        }

        .bg-animated {
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 25%, #0f0f0f 50%, #151515 75%, #000000 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            33% { transform: translateY(-10px) rotate(1deg); }
            66% { transform: translateY(5px) rotate(-1deg); }
        }

        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 255, 255, 0.1); }
            50% { box-shadow: 0 0 40px rgba(255, 255, 255, 0.2); }
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        @keyframes bounce-in {
            0% { transform: scale(0.3) translateY(50px); opacity: 0; }
            50% { transform: scale(1.05); }
            70% { transform: scale(0.9); }
            100% { transform: scale(1) translateY(0); opacity: 1; }
        }

        .animate-bounce-in {
            animation: bounce-in 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        }

        .animate-float {
            animation: float 6s ease-in-out infinite;
        }

        .animate-glow {
            animation: pulse-glow 3s ease-in-out infinite;
        }

        .glass {
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            background: var(--glass-bg);
            border: 1px solid var(--glass-border);
            box-shadow: var(--glass-shadow);
        }

        .glass-strong {
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        }

        /* Custom Input Styles */
        .glass-input {
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            transition: all 0.3s ease;
        }

        .glass-input:focus {
            outline: none;
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.3);
            box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.1);
            transform: translateY(-2px);
        }

        .glass-input::placeholder {
            color: rgba(255, 255, 255, 0.4);
        }

        /* Custom Button Styles - Minimalist Black & White */
        .glass-button {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(240, 240, 240, 0.9));
            border: 1px solid rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            color: #000000;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .glass-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s;
        }

        .glass-button:hover::before {
            left: 100%;
        }

        .glass-button:hover {
            transform: translateY(-2px) scale(1.02);
            box-shadow: 0 10px 30px rgba(255, 255, 255, 0.2);
            background: linear-gradient(135deg, rgba(255, 255, 255, 1), rgba(255, 255, 255, 1));
        }

        .glass-button:active {
            transform: translateY(0) scale(0.98);
        }

        /* Alert Styles */
        .alert-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            backdrop-filter: blur(10px);
            color: rgb(254, 202, 202);
        }

        .alert-success {
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            backdrop-filter: blur(10px);
            color: rgb(187, 247, 208);
        }

        .alert-info {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(10px);
            color: rgb(229, 229, 229);
        }

        /* Loading Animation */
        .loading-spinner {
            border: 3px solid rgba(255, 255, 255, 0.2);
            border-top: 3px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(45deg, rgba(255, 255, 255, 0.3), rgba(255, 255, 255, 0.2));
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(45deg, rgba(255, 255, 255, 0.5), rgba(255, 255, 255, 0.4));
        }

        /* Responsive Design */
        @media (max-width: 640px) {
            .main-container {
                margin: 1rem;
                padding: 2rem;
            }
        }

        /* Link Styles */
        .glass-link {
            color: rgba(255, 255, 255, 0.7);
            transition: all 0.3s ease;
        }

        .glass-link:hover {
            color: white;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
        }

        /* Form Label Styles */
        .glass-label {
            color: var(--text-secondary);
            font-weight: 500;
            margin-bottom: 0.5rem;
            display: block;
        }

        /* Logo Container Styles */
        .logo-container {
            width: 120px;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }

        .logo-container img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            filter: drop-shadow(0 4px 20px rgba(255, 255, 255, 0.1));
            transition: all 0.3s ease;
        }

        .logo-container:hover img {
            filter: drop-shadow(0 8px 30px rgba(255, 255, 255, 0.2));
            transform: scale(1.05);
        }

        .logo-glow {
            position: absolute;
            inset: -20px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
            border-radius: 50%;
            animation: pulse-glow 3s ease-in-out infinite;
            z-index: -1;
        }
    </style>
</head>

<body class="bg-animated">
    <!-- Animated Background Elements - Minimalist White Particles -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div class="absolute -top-20 -left-20 w-96 h-96 bg-gradient-to-br from-white/5 to-white/10 rounded-full blur-3xl animate-pulse"></div>
        <div class="absolute top-1/2 -right-20 w-80 h-80 bg-gradient-to-br from-white/5 to-white/10 rounded-full blur-3xl animate-pulse" style="animation-delay: 2s;"></div>
        <div class="absolute -bottom-20 left-1/3 w-72 h-72 bg-gradient-to-br from-white/5 to-white/10 rounded-full blur-3xl animate-pulse" style="animation-delay: 4s;"></div>
        
        <!-- Floating particles -->
        <div class="absolute top-1/4 left-1/4 w-2 h-2 bg-white/20 rounded-full animate-ping" style="animation-delay: 1s;"></div>
        <div class="absolute top-3/4 right-1/4 w-3 h-3 bg-white/10 rounded-full animate-ping" style="animation-delay: 3s;"></div>
        <div class="absolute top-1/2 left-1/6 w-1 h-1 bg-white/15 rounded-full animate-ping" style="animation-delay: 5s;"></div>
    </div>

    <div class="min-h-screen flex items-center justify-center p-4 relative z-10">
        <div class="main-container glass-strong rounded-3xl p-8 w-full max-w-md animate-bounce-in">
            <!-- Logo Section with Image -->
            <div class="flex justify-center mb-8">
                <div class="logo-container animate-float">
                    <div class="logo-glow"></div>
                    <img src="${url.resourcesPath}/img/logo.svg" alt="Logo" />
                </div>
            </div>

            <!-- Header Section -->
            <#nested "header">

            <!-- Main Content -->
            <div class="space-y-6">
                <!-- Messages -->
                <#if displayMessage && message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                    <div class="alert-${message.type} rounded-2xl p-4 text-center backdrop-blur-sm">
                        <#if message.type = 'success'>
                            <div class="flex items-center justify-center mb-2">
                                <span class="text-2xl">✅</span>
                            </div>
                        </#if>
                        <#if message.type = 'error'>
                            <div class="flex items-center justify-center mb-2">
                                <span class="text-2xl">❌</span>
                            </div>
                        </#if>
                        <#if message.type = 'info'>
                            <div class="flex items-center justify-center mb-2">
                                <span class="text-2xl">ℹ️</span>
                            </div>
                        </#if>
                        ${kcSanitize(message.summary)?no_esc}
                    </div>
                </#if>

                <!-- Form Content -->
                <#nested "form">

                <!-- Info Section -->
                <#if displayInfo>
                    <#nested "info">
                </#if>
            </div>

            <!-- Footer -->
            <div class="mt-8 pt-6 border-t border-white/10 text-center">
                <p class="text-white/40 text-sm">
                    Secure authentication powered by Keycloak
                </p>
                <div class="flex justify-center space-x-1 mt-2">
                    <div class="w-1 h-1 bg-white/20 rounded-full animate-pulse"></div>
                    <div class="w-1 h-1 bg-white/20 rounded-full animate-pulse" style="animation-delay: 0.3s;"></div>
                    <div class="w-1 h-1 bg-white/20 rounded-full animate-pulse" style="animation-delay: 0.6s;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Overlay (hidden by default) -->
    <div id="loading-overlay" class="fixed inset-0 bg-black/70 backdrop-blur-sm hidden items-center justify-center z-50">
        <div class="glass rounded-2xl p-8 text-center">
            <div class="loading-spinner w-12 h-12 mx-auto mb-4"></div>
            <p class="text-white">Processing...</p>
        </div>
    </div>

    <script>
        // Add loading states to forms
        document.addEventListener('DOMContentLoaded', function() {
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', function() {
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        const originalText = submitBtn.textContent;
                        submitBtn.innerHTML = '<div class="loading-spinner w-5 h-5 inline-block mr-2"></div>' + 'Processing...';
                        
                        // Re-enable after 5 seconds as fallback
                        setTimeout(() => {
                            submitBtn.disabled = false;
                            submitBtn.textContent = originalText;
                        }, 5000);
                    }
                });
            });

            // Add focus effects to inputs
            const inputs = document.querySelectorAll('input');
            inputs.forEach(input => {
                input.addEventListener('focus', function() {
                    this.parentElement.style.transform = 'translateY(-2px)';
                });
                
                input.addEventListener('blur', function() {
                    this.parentElement.style.transform = 'translateY(0)';
                });
            });
        });
    </script>
</body>

</html>
</#macro>