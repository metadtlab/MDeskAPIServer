package kr.co.mdesk.domain.user;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.LocalDate;

@Entity
@Table(name = "api_userprofile")
public class UserProfile {

    @Id
    @Column(name = "id")
    private Long id;

    @Column(name = "username", unique = true, length = 50)
    private String username;

    @Column(name = "password", length = 128)
    private String password;

    @Column(name = "rid", length = 16)
    private String rid;

    @Column(name = "uuid", length = 60)
    private String uuid;

    @Column(name = "autologin")
    private Boolean autoLogin;

    @Column(name = "rtype", length = 20)
    private String rtype;

    @Column(name = "deviceinfo")
    private String deviceInfo;

    @Column(name = "company_name", length = 100)
    private String companyName;

    @Column(name = "email", length = 254)
    private String email;

    @Column(name = "phone", length = 20)
    private String phone;

    @Column(name = "membership_level", length = 20)
    private String membershipLevel;

    @Column(name = "membership_start")
    private LocalDate membershipStart;

    @Column(name = "membership_expires")
    private LocalDate membershipExpires;

    @Column(name = "max_agents")
    private Integer maxAgents;

    @Column(name = "relay_server", length = 100)
    private String relayServer;

    @Column(name = "is_active")
    private Boolean isActive;

    @Column(name = "is_admin")
    private Boolean isAdmin;

    public Long getId() {
        return id;
    }

    public String getUsername() {
        return username;
    }

    public String getPassword() {
        return password;
    }

    public String getRid() {
        return rid;
    }

    public void setRid(String rid) {
        this.rid = rid;
    }

    public String getUuid() {
        return uuid;
    }

    public void setUuid(String uuid) {
        this.uuid = uuid;
    }

    public Boolean getAutoLogin() {
        return autoLogin;
    }

    public void setAutoLogin(Boolean autoLogin) {
        this.autoLogin = autoLogin;
    }

    public String getRtype() {
        return rtype;
    }

    public void setRtype(String rtype) {
        this.rtype = rtype;
    }

    public String getDeviceInfo() {
        return deviceInfo;
    }

    public void setDeviceInfo(String deviceInfo) {
        this.deviceInfo = deviceInfo;
    }

    public String getCompanyName() {
        return companyName;
    }

    public String getEmail() {
        return email;
    }

    public String getPhone() {
        return phone;
    }

    public String getMembershipLevel() {
        return membershipLevel;
    }

    public LocalDate getMembershipStart() {
        return membershipStart;
    }

    public LocalDate getMembershipExpires() {
        return membershipExpires;
    }

    public Integer getMaxAgents() {
        return maxAgents;
    }

    public String getRelayServer() {
        return relayServer;
    }

    public Boolean getIsActive() {
        return isActive;
    }

    public Boolean getIsAdmin() {
        return isAdmin;
    }
}
