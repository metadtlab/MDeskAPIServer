package kr.co.mdesk.controller.web;

import java.util.Map;
import jakarta.validation.Valid;
import kr.co.mdesk.dto.request.WebLoginRequest;
import kr.co.mdesk.dto.response.WebLoginResponse;
import kr.co.mdesk.service.auth.AuthService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/web/auth")
public class WebAuthController {

    private final AuthService authService;

    public WebAuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ResponseEntity<WebLoginResponse> login(@Valid @RequestBody WebLoginRequest request) {
        return ResponseEntity.ok(authService.loginWeb(request));
    }

    @PostMapping("/logout")
    public ResponseEntity<Map<String, Object>> logout() {
        return ResponseEntity.ok(Map.of("code", 1));
    }

    @PostMapping("/register")
    public ResponseEntity<Map<String, Object>> register() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    @PostMapping("/find-password")
    public ResponseEntity<Map<String, Object>> findPassword() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }

    @PostMapping("/reset-password")
    public ResponseEntity<Map<String, Object>> resetPassword() {
        return ResponseEntity.status(501).body(Map.of("error", "not_implemented"));
    }
}
