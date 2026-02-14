package kr.co.mdesk.config;

import kr.co.mdesk.security.BearerTokenAuthenticationFilter;
import kr.co.mdesk.security.JwtAuthenticationFilter;
import kr.co.mdesk.service.auth.DjangoPasswordEncoder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(
        HttpSecurity http,
        JwtAuthenticationFilter jwtAuthenticationFilter,
        BearerTokenAuthenticationFilter bearerTokenAuthenticationFilter
    ) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .cors(Customizer.withDefaults())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .exceptionHandling(ex -> ex.authenticationEntryPoint((request, response, authException) -> {
                response.setStatus(401);
                response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                response.getWriter().write("{\"error\":\"unauthorized\"}");
            }))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers(
                    "/swagger-ui/**",
                    "/swagger-ui.html",
                    "/v3/api-docs/**",
                    "/api/login",
                    "/api/sysinfo",
                    "/api/heartbeat",
                    "/api/audit/**",
                    "/api/sessions/**",
                    "/api/custom_app_config",
                    "/api/version/latest",
                    "/api/download/**",
                    "/api/certno/**",
                    "/api/device/register",
                    "/api/device/unregister",
                    "/api/agentnumupdate/**",
                    "/api/agentclose/**",
                    "/api/*/public_agents",
                    "/api/verify_remote_user",
                    "/api/web/auth/login",
                    "/api/web/auth/register",
                    "/api/web/auth/find-password",
                    "/api/web/auth/reset-password"
                ).permitAll()
                .anyRequest().authenticated()
            )
            .addFilterBefore(bearerTokenAuthenticationFilter, UsernamePasswordAuthenticationFilter.class)
            .addFilterBefore(jwtAuthenticationFilter, BearerTokenAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder(DjangoPasswordEncoder djangoPasswordEncoder) {
        return djangoPasswordEncoder;
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        return configuration.getAuthenticationManager();
    }
}
