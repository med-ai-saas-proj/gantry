<#import "template.ftl" as layout>
<@layout.registrationLayout displayMessage=!messagesPerField.existsError('firstName','lastName','email','username','password','password-confirm'); section>
    <#if section = "header">
        <div class="text-center mb-6">
            <h1 class="text-3xl font-bold text-white mb-2 animate-float">
                Create Account
            </h1>
            <p class="text-white/60">
                Join us today and get started
            </p>
        </div>
    <#elseif section = "form">
        <form id="kc-register-form" action="${url.registrationAction}" method="post" class="space-y-6">
            <!-- Dynamic Form Fields Based on Profile Configuration -->
            <#list profile.attributes as attribute>
                <#if attribute.name == "firstName" || attribute.name == "lastName">
                    <!-- First Name & Last Name in a row -->
                    <#if attribute.name == "firstName" && profile.attributes?seq_contains(profile.attributes?filter(attr -> attr.name == "lastName")?first)>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <!-- First Name -->
                            <div class="space-y-2">
                                <label for="firstName" class="glass-label">
                                    ${msg("firstName")} 
                                    <#if attribute.required><span class="text-red-400">*</span></#if>
                                </label>
                                <div class="relative group">
                                    <input type="text" id="firstName" name="firstName" 
                                           value="${(register.formData.firstName!'')}"
                                           class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                           placeholder="${msg("firstName")}"
                                           <#if messagesPerField.existsError('firstName')>aria-invalid="true"</#if>/>
                                    <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                                </div>
                                <#if messagesPerField.existsError('firstName')>
                                    <div class="text-red-300 text-sm mt-1 flex items-center">
                                        <span class="mr-1">⚠️</span>
                                        ${kcSanitize(messagesPerField.get('firstName'))?no_esc}
                                    </div>
                                </#if>
                            </div>

                            <!-- Last Name -->
                            <#assign lastNameAttr = profile.attributes?filter(attr -> attr.name == "lastName")?first>
                            <div class="space-y-2">
                                <label for="lastName" class="glass-label">
                                    ${msg("lastName")} 
                                    <#if lastNameAttr.required><span class="text-red-400">*</span></#if>
                                </label>
                                <div class="relative group">
                                    <input type="text" id="lastName" name="lastName" 
                                           value="${(register.formData.lastName!'')}"
                                           class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                           placeholder="${msg("lastName")}"
                                           <#if messagesPerField.existsError('lastName')>aria-invalid="true"</#if>/>
                                    <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                                </div>
                                <#if messagesPerField.existsError('lastName')>
                                    <div class="text-red-300 text-sm mt-1 flex items-center">
                                        <span class="mr-1">⚠️</span>
                                        ${kcSanitize(messagesPerField.get('lastName'))?no_esc}
                                    </div>
                                </#if>
                            </div>
                        </div>
                    </#if>
                <#elseif attribute.name == "email">
                    <!-- Email Field -->
                    <div class="space-y-2">
                        <label for="email" class="glass-label">
                            ${msg("email")} 
                            <#if attribute.required><span class="text-red-400">*</span></#if>
                        </label>
                        <div class="relative group">
                            <input type="email" id="email" name="email" 
                                   value="${(register.formData.email!'')}" autocomplete="email"
                                   class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                   placeholder="${msg("email")}"
                                   <#if messagesPerField.existsError('email')>aria-invalid="true"</#if>/>
                            <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        </div>
                        <#if messagesPerField.existsError('email')>
                            <div class="text-red-300 text-sm mt-1 flex items-center">
                                <span class="mr-1">⚠️</span>
                                ${kcSanitize(messagesPerField.get('email'))?no_esc}
                            </div>
                        </#if>
                    </div>
                <#elseif attribute.name == "username" && !realm.registrationEmailAsUsername>
                    <!-- Username Field -->
                    <div class="space-y-2">
                        <label for="username" class="glass-label">
                            ${msg("username")} 
                            <#if attribute.required><span class="text-red-400">*</span></#if>
                        </label>
                        <div class="relative group">
                            <input type="text" id="username" name="username" 
                                   value="${(register.formData.username!'')}" autocomplete="username"
                                   class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                   placeholder="${msg("username")}"
                                   <#if messagesPerField.existsError('username')>aria-invalid="true"</#if>/>
                            <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        </div>
                        <#if messagesPerField.existsError('username')>
                            <div class="text-red-300 text-sm mt-1 flex items-center">
                                <span class="mr-1">⚠️</span>
                                ${kcSanitize(messagesPerField.get('username'))?no_esc}
                            </div>
                        </#if>
                    </div>
                <#elseif attribute.name != "lastName" && attribute.name != "firstName" && attribute.name != "email" && attribute.name != "username">
                    <!-- Other Custom Attributes -->
                    <div class="space-y-2">
                        <label for="${attribute.name}" class="glass-label">
                            ${advancedMsg(attribute.displayName!'')} 
                            <#if attribute.required><span class="text-red-400">*</span></#if>
                        </label>
                        <div class="relative group">
                            <input type="text" id="${attribute.name}" name="${attribute.name}" 
                                   value="${(register.formData[attribute.name]!'')}"
                                   class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                                   placeholder="${advancedMsg(attribute.displayName!'')}"
                                   <#if messagesPerField.existsError('${attribute.name}')>aria-invalid="true"</#if>/>
                            <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                        </div>
                        <#if messagesPerField.existsError('${attribute.name}')>
                            <div class="text-red-300 text-sm mt-1 flex items-center">
                                <span class="mr-1">⚠️</span>
                                ${kcSanitize(messagesPerField.get('${attribute.name}'))?no_esc}
                            </div>
                        </#if>
                    </div>
                </#if>
            </#list>

            <!-- Password Fields (always present) -->
            <#if passwordRequired??>
                <div class="space-y-2">
                    <label for="password" class="glass-label">
                        ${msg("password")} <span class="text-red-400">*</span>
                    </label>
                    <div class="relative group">
                        <input type="password" id="password" name="password" autocomplete="new-password"
                               class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                               placeholder="${msg("password")}"
                               <#if messagesPerField.existsError('password')>aria-invalid="true"</#if>/>
                        <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                    </div>
                    <#if messagesPerField.existsError('password')>
                        <div class="text-red-300 text-sm mt-1 flex items-center">
                            <span class="mr-1">⚠️</span>
                            ${kcSanitize(messagesPerField.get('password'))?no_esc}
                        </div>
                    </#if>
                </div>

                <div class="space-y-2">
                    <label for="password-confirm" class="glass-label">
                        ${msg("passwordConfirm")} <span class="text-red-400">*</span>
                    </label>
                    <div class="relative group">
                        <input type="password" id="password-confirm" name="password-confirm"
                               class="glass-input w-full px-4 py-3 rounded-xl text-white placeholder-white/60 transition-all duration-300"
                               placeholder="${msg("passwordConfirm")}"
                               <#if messagesPerField.existsError('password-confirm')>aria-invalid="true"</#if>/>
                        <div class="absolute inset-0 rounded-xl bg-gradient-to-r from-white/10 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                    </div>
                    <#if messagesPerField.existsError('password-confirm')>
                        <div class="text-red-300 text-sm mt-1 flex items-center">
                            <span class="mr-1">⚠️</span>
                            ${kcSanitize(messagesPerField.get('password-confirm'))?no_esc}
                        </div>
                    </#if>
                </div>
            </#if>

            <!-- Terms and Conditions (if enabled) -->
            <#if recaptchaRequired??>
                <div class="recaptcha-container">
                    <div class="g-recaptcha" data-size="compact" data-sitekey="${recaptchaSiteKey}"></div>
                </div>
            </#if>

            <!-- Action Buttons -->
            <div class="flex flex-col sm:flex-row gap-4 pt-4">
                <button type="submit" 
                        class="glass-button flex-1 py-3 px-6 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transform transition-all duration-300">
                    ${msg("doRegister")}
                </button>
                
                <a href="${url.loginUrl}" 
                   class="glass flex-1 py-3 px-6 rounded-xl text-white font-medium text-center hover:bg-white/10 transition-all duration-300">
                    ← Back to Login
                </a>
            </div>
        </form>

        <!-- Social Providers -->
        <#if realm.password && social.providers??>
            <div class="mt-6">
                <div class="relative">
                    <div class="absolute inset-0 flex items-center">
                        <div class="w-full border-t border-white/10"></div>
                    </div>
                    <div class="relative flex justify-center text-sm">
                        <span class="px-4 bg-transparent text-white/50">Or register with</span>
                    </div>
                </div>

                <div class="mt-4 space-y-3">
                    <#list social.providers as p>
                        <a id="social-${p.alias}" href="${p.loginUrl}" 
                           class="glass w-full flex justify-center items-center px-4 py-3 rounded-xl text-white hover:bg-white/10 transition-all duration-300 group">
                            <#if p.iconClasses?has_content>
                                <i class="${p.iconClasses}" aria-hidden="true"></i>
                                <span class="ml-2">${p.displayName!}</span>
                            <#else>
                                <span>${p.displayName!}</span>
                            </#if>
                        </a>
                    </#list>
                </div>
            </div>
        </#if>
    </#if>
</@layout.registrationLayout>