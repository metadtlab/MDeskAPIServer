package kr.co.mdesk.security;

import kr.co.mdesk.domain.user.UserProfile;
import kr.co.mdesk.repository.user.UserProfileRepository;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

@Service
public class CustomUserDetailsService implements UserDetailsService {

    private final UserProfileRepository userProfileRepository;

    public CustomUserDetailsService(UserProfileRepository userProfileRepository) {
        this.userProfileRepository = userProfileRepository;
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        UserProfile user = userProfileRepository.findByUsername(username)
            .orElseThrow(() -> new UsernameNotFoundException("user not found"));

        return User.withUsername(user.getUsername())
            .password(user.getPassword())
            .roles(Boolean.TRUE.equals(user.getIsAdmin()) ? "ADMIN" : "USER")
            .disabled(Boolean.FALSE.equals(user.getIsActive()))
            .build();
    }
}
