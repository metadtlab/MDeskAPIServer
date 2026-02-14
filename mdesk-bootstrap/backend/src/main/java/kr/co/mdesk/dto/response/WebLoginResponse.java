package kr.co.mdesk.dto.response;

public record WebLoginResponse(
    String accessToken,
    String tokenType,
    long expiresIn,
    String username,
    Long userId,
    boolean isAdmin
) {
}
