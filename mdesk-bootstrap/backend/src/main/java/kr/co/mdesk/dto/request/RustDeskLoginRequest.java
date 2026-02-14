package kr.co.mdesk.dto.request;

import com.fasterxml.jackson.annotation.JsonProperty;

public class RustDeskLoginRequest {

    private String username;
    private String password;
    @JsonProperty("id")
    private String rid;
    private String uuid;
    private Boolean autoLogin;
    @JsonProperty("type")
    private String rtype;
    private Object deviceInfo;

    public String getUsername() {
        return username;
    }

    public String getPassword() {
        return password;
    }

    public String getRid() {
        return rid;
    }

    public String getUuid() {
        return uuid;
    }

    public Boolean getAutoLogin() {
        return autoLogin;
    }

    public String getRtype() {
        return rtype;
    }

    public Object getDeviceInfo() {
        return deviceInfo;
    }
}
