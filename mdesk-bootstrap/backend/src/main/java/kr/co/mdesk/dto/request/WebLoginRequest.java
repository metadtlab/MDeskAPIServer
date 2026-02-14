package kr.co.mdesk.dto.request;

import jakarta.validation.constraints.NotBlank;

public class WebLoginRequest {
    @NotBlank
    private String username;
    @NotBlank
    private String password;

    public String getUsername() {
        return username;
    }

    public String getPassword() {
        return password;
    }
}
