package kr.co.mdesk.service.auth;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import kr.co.mdesk.config.JwtProperties;
import kr.co.mdesk.domain.user.UserProfile;
import kr.co.mdesk.domain.work.RustDeskToken;
import kr.co.mdesk.dto.request.RustDeskLoginRequest;
import kr.co.mdesk.dto.request.RustDeskLogoutRequest;
import kr.co.mdesk.dto.request.WebLoginRequest;
import kr.co.mdesk.dto.response.WebLoginResponse;
import kr.co.mdesk.repository.user.UserProfileRepository;
import kr.co.mdesk.repository.work.RustDeskTokenRepository;
import kr.co.mdesk.security.JwtTokenProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

    private final UserProfileRepository userProfileRepository;
    private final RustDeskTokenRepository rustDeskTokenRepository;
    private final PasswordEncoder passwordEncoder;
    private final AuthenticationManager authenticationManager;
    private final JwtTokenProvider jwtTokenProvider;
    private final JwtProperties jwtProperties;
    private final ObjectMapper objectMapper;

    @Value("${mdesk.token-effective-seconds:7200}")
    private long tokenEffectiveSeconds;

    public AuthService(
        UserProfileRepository userProfileRepository,
        RustDeskTokenRepository rustDeskTokenRepository,
        PasswordEncoder passwordEncoder,
        AuthenticationManager authenticationManager,
        JwtTokenProvider jwtTokenProvider,
        JwtProperties jwtProperties,
        ObjectMapper objectMapper
    ) {
        this.userProfileRepository = userProfileRepository;
        this.rustDeskTokenRepository = rustDeskTokenRepository;
        this.passwordEncoder = passwordEncoder;
        this.authenticationManager = authenticationManager;
        this.jwtTokenProvider = jwtTokenProvider;
        this.jwtProperties = jwtProperties;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> loginRustDesk(RustDeskLoginRequest request) {
        Map<String, Object> result = new HashMap<>();
        Optional<UserProfile> optionalUser = userProfileRepository.findByUsername(request.getUsername());
        if (optionalUser.isEmpty()) {
            result.put("error", "계정 또는 비밀번호가 틀렸습니다!");
            return result;
        }
        UserProfile user = optionalUser.get();
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            result.put("error", "계정 또는 비밀번호가 틀렸습니다!");
            return result;
        }

        user.setRid(request.getRid());
        user.setUuid(request.getUuid());
        user.setAutoLogin(request.getAutoLogin() == null ? Boolean.TRUE : request.getAutoLogin());
        user.setRtype(request.getRtype());
        try {
            user.setDeviceInfo(objectMapper.writeValueAsString(request.getDeviceInfo()));
        } catch (Exception ignored) {
            user.setDeviceInfo("{}");
        }
        userProfileRepository.save(user);

        RustDeskToken token = rustDeskTokenRepository.findFirstByUidAndUsernameAndRid(
            String.valueOf(user.getId()), user.getUsername(), user.getRid()).orElse(null);

        if (token != null && token.getCreateTime() != null) {
            long age = Duration.between(token.getCreateTime(), LocalDateTime.now()).getSeconds();
            if (age >= tokenEffectiveSeconds) {
                rustDeskTokenRepository.delete(token);
                token = null;
            }
        }
        if (token == null) {
            token = new RustDeskToken();
            token.setUsername(user.getUsername());
            token.setUid(String.valueOf(user.getId()));
            token.setRid(user.getRid());
            token.setUuid(user.getUuid());
            token.setCreateTime(LocalDateTime.now());
            token.setAccessToken(generateMd5(user.getUsername() + ":" + System.currentTimeMillis() + ":" + UUID.randomUUID()));
            rustDeskTokenRepository.save(token);
        }

        result.put("access_token", token.getAccessToken());
        result.put("type", "access_token");
        Map<String, Object> userNode = new HashMap<>();
        userNode.put("user_pkid", user.getId());
        userNode.put("name", user.getUsername());
        userNode.put("email", user.getEmail());
        userNode.put("phone", user.getPhone());
        userNode.put("company_name", user.getCompanyName());
        userNode.put("membership_level", user.getMembershipLevel());
        userNode.put("membership_start", user.getMembershipStart());
        userNode.put("membership_expires", user.getMembershipExpires());
        userNode.put("max_agents", user.getMaxAgents());
        userNode.put("relay_server", user.getRelayServer());
        userNode.put("relay_pub_key", "");
        userNode.put("is_admin", Boolean.TRUE.equals(user.getIsAdmin()));
        result.put("user", userNode);
        return result;
    }

    @Transactional
    public Map<String, Object> logoutRustDesk(RustDeskLogoutRequest request) {
        Map<String, Object> result = new HashMap<>();
        Optional<UserProfile> user = userProfileRepository.findByRidAndUuid(request.getRid(), request.getUuid());
        if (user.isEmpty()) {
            result.put("error", "비정상적인 요청!");
            return result;
        }
        rustDeskTokenRepository.findFirstByUidAndRid(String.valueOf(user.get().getId()), user.get().getRid())
            .ifPresent(rustDeskTokenRepository::delete);
        result.put("code", 1);
        return result;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> currentUser(String tokenValue) {
        Map<String, Object> result = new HashMap<>();
        RustDeskToken token = rustDeskTokenRepository.findByAccessToken(tokenValue).orElse(null);
        if (token == null) {
            result.put("error", "유효하지 않은 토큰입니다.");
            return result;
        }
        UserProfile user = userProfileRepository.findById(Long.parseLong(token.getUid())).orElse(null);
        if (user == null) {
            result.put("error", "사용자를 찾을 수 없습니다.");
            return result;
        }
        result.put("access_token", token.getAccessToken());
        result.put("type", "access_token");
        result.put("name", user.getUsername());
        return result;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> userInfo(String tokenValue) {
        Map<String, Object> result = new HashMap<>();
        RustDeskToken token = rustDeskTokenRepository.findByAccessToken(tokenValue).orElse(null);
        if (token == null) {
            result.put("error", "유효하지 않은 토큰입니다.");
            return result;
        }
        UserProfile user = userProfileRepository.findById(Long.parseLong(token.getUid())).orElse(null);
        if (user == null) {
            result.put("error", "사용자를 찾을 수 없습니다.");
            return result;
        }
        Map<String, Object> data = new HashMap<>();
        data.put("user_pkid", user.getId());
        data.put("username", user.getUsername());
        data.put("email", user.getEmail());
        data.put("phone", user.getPhone());
        data.put("company_name", user.getCompanyName());
        data.put("membership_level", user.getMembershipLevel());
        data.put("membership_start", user.getMembershipStart());
        data.put("membership_expires", user.getMembershipExpires());
        data.put("max_agents", user.getMaxAgents());
        data.put("relay_server", user.getRelayServer());
        data.put("relay_pub_key", "");
        data.put("is_admin", Boolean.TRUE.equals(user.getIsAdmin()));
        data.put("is_active", !Boolean.FALSE.equals(user.getIsActive()));
        result.put("code", 1);
        result.put("data", data);
        return result;
    }

    @Transactional(readOnly = true)
    public WebLoginResponse loginWeb(WebLoginRequest request) {
        try {
            authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(request.getUsername(), request.getPassword()));
            UserProfile user = userProfileRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new BadCredentialsException("invalid credentials"));
            return new WebLoginResponse(
                jwtTokenProvider.createAccessToken(user.getUsername(), user.getId()),
                "Bearer",
                jwtProperties.getAccessTokenExpiration() / 1000,
                user.getUsername(),
                user.getId(),
                Boolean.TRUE.equals(user.getIsAdmin()));
        } catch (Exception ex) {
            throw new BadCredentialsException("invalid credentials", ex);
        }
    }

    private String generateMd5(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("MD5");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception ex) {
            throw new IllegalStateException("md5 generation failed", ex);
        }
    }
}
