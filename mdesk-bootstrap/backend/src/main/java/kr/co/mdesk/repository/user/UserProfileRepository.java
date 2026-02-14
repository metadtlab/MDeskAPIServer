package kr.co.mdesk.repository.user;

import java.util.Optional;
import kr.co.mdesk.domain.user.UserProfile;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserProfileRepository extends JpaRepository<UserProfile, Long> {

    Optional<UserProfile> findByUsername(String username);

    Optional<UserProfile> findByRidAndUuid(String rid, String uuid);
}
