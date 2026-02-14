package kr.co.mdesk.controller.api;

import java.util.Map;
import kr.co.mdesk.dto.request.RustDeskLoginRequest;
import kr.co.mdesk.dto.request.RustDeskLogoutRequest;
import kr.co.mdesk.service.auth.AuthService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<Map<String, Object>> login(@RequestBody RustDeskLoginRequest request) {
        return ResponseEntity.ok(authService.loginRustDesk(request));
    }

    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout(@RequestBody RustDeskLogoutRequest request) {
        return ResponseEntity.ok(authService.logoutRustDesk(request));
    }

    @PostMapping("/currentUser")
    public ResponseEntity<Map<String, Object>> currentUser(
        @RequestHeader(value = "Authorization", required = false) String authorization
    ) {
        String token = extractBearerToken(authorization);
        if (token == null) {
            return ResponseEntity.status(401).body(Map.of("error", "인증 토큰이 필요합니다."));
        }
        Map<String, Object> body = authService.currentUser(token);
        return body.containsKey("error") ? ResponseEntity.status(401).body(body) : ResponseEntity.ok(body);
    }

    @PostMapping("/userInfo")
    public ResponseEntity<Map<String, Object>> userInfo(
        @RequestHeader(value = "Authorization", required = false) String authorization
    ) {
        String token = extractBearerToken(authorization);
        if (token == null) {
            return ResponseEntity.status(401).body(Map.of("error", "인증 토큰이 필요합니다."));
        }
        Map<String, Object> body = authService.userInfo(token);
        return body.containsKey("error") ? ResponseEntity.status(401).body(body) : ResponseEntity.ok(body);
    }

    @PostMapping("/verify_remote_user")
    public ResponseEntity<Map<String, Object>> verifyRemoteUser() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    @GetMapping("/users")
    public ResponseEntity<Map<String, Object>> users() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    @GetMapping("/peers")
    public ResponseEntity<Map<String, Object>> peers() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    @GetMapping("/group")
    public ResponseEntity<Map<String, Object>> group() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    private String extractBearerToken(String authorization) {
        if (authorization == null || !authorization.startsWith("Bearer ")) {
            return null;
        }
        return authorization.substring(7);
    }
}
