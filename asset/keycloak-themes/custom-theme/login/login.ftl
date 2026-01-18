<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('username','password') displayInfo=realm.password && realm.registrationAllowed && !registrationDisabled??; section>
    <#if section = "header">
        <div class="text-center mb-6">
            <h1 class="text-3xl font-bold text-white mb-2 animate-float">
                Med AI
            </h1>
            <p class="text-white/60">
                Sign in to your account
            </p>
        </div>
    <#elseif section = "form">
        <div id="kc-form">
            <div id="kc-form-wrapper">
                <form id="kc-form-login" onsubmit="login.disabled = true; return true;" action="${url.loginAction}" method="post" class="space-y-6">
                    <!-- Username/Email Field -->
                    <div class="space-y-2">
                        <label for="username" class="glass-label">
                            <#if !realm.loginWithEmailAllowed>
                                ${msg("username")}
                            <#elseif !realm.registrationEmailAsUsername>
                                ${msg("usernameOrEmail")}
                            <#else>
                                ${msg("email")}
                            </#if>
                        </label>
                        <div class="relative group">
                            <input tabindex="1" id="username" name="username"
                                   value="${(login.username!'')}"
                                   type="text" autofocus autocomplete="off"
                                   class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                   placeholder="<#if !realm.loginWithEmailAllowed>${msg("username")}<#elseif !realm.registrationEmailAsUsername>${msg("usernameOrEmail")}<#else>${msg("email")}</#if>"
                                   <#if messagesPerField.existsError('username','password')>aria-invalid="true"</#if>/>
                            <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        </div>
                        <#if messagesPerField.existsError('username','password')>
                            <div class="text-red-300 text-sm mt-1 flex items-center">
                                <span class="mr-1">⚠️</span>
                                ${kcSanitize(messagesPerField.getFirstError('username','password'))?no_esc}
                            </div>
                        </#if>
                    </div>

                    <!-- Password Field -->
                    <div class="space-y-2">
                        <label for="password" class="glass-label">
                            ${msg("password")}
                        </label>
                        <div class="relative group">
                            <input tabindex="2" id="password" name="password"
                                   type="password" autocomplete="current-password"
                                   class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                   placeholder="${msg("password")}"
                                   <#if messagesPerField.existsError('username','password')>aria-invalid="true"</#if>/>
                            <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        </div>
                    </div>

                    <!-- Remember Me & Forgot Password -->
                    <div class="flex items-center justify-between text-sm">
                        <#if realm.rememberMe && !usernameEditDisabled??>
                            <label class="flex items-center space-x-2 text-white/60 hover:text-white cursor-pointer transition-colors duration-200">
                                <input tabindex="3" id="rememberMe" name="rememberMe" type="checkbox"
                                       class="w-4 h-4 rounded border-2 border-white/30 bg-white/10 text-white focus:ring-white/30 focus:ring-2"
                                       <#if login.rememberMe??>checked</#if>>
                                <span>${msg("rememberMe")}</span>
                            </label>
                        <#else>
                            <div></div>
                        </#if>

                        <#if realm.resetPasswordAllowed>
                            <a tabindex="5" href="${url.loginResetCredentialsUrl}" class="glass-link text-sm hover:underline">
                                ${msg("doForgotPassword")}
                            </a>
                        </#if>
                    </div>

                    <!-- Login Button -->
                    <div class="space-y-4">
                        <button tabindex="4" name="login" id="kc-login" type="submit"
                                class="glass-button w-full py-3 px-6 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transform transition-all duration-300">
                            ${msg("doLogIn")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    <#elseif section = "info">
        <#if realm.password && realm.registrationAllowed && !registrationDisabled??>
            <div class="text-center mt-6 p-4 glass rounded-2xl">
                <p class="text-white/60 mb-3">
                    ${msg("noAccount")}
                </p>
                <a tabindex="6" href="${url.registrationUrl}"
                   class="glass-button inline-flex items-center px-6 py-2 rounded-xl font-medium transition-all duration-300">
                    ${msg("doRegister")}
                </a>
            </div>
        </#if>
    </#if>
</@layout.registrationLayout>
