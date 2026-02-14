package kr.co.mdesk.dto.request;

import com.fasterxml.jackson.annotation.JsonProperty;

public class RustDeskLogoutRequest {
    @JsonProperty("id")
    private String rid;
    private String uuid;

    public String getRid() {
        return rid;
    }

    public String getUuid() {
        return uuid;
    }
}
