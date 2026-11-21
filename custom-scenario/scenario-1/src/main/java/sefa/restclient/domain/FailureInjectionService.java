package sefa.restclient.domain;

import com.netflix.appinfo.InstanceInfo;
import com.netflix.discovery.EurekaClient;
import com.netflix.discovery.shared.Application;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.util.Timer;
import java.util.TimerTask;

/**
 * Stops a restaurant instance at the configured times, and restarts it after the
 * configured duration (0 = it stays stopped).
 *
 * Changed from the RAMSES original: it no longer stops a fixed instance id
 * (ID_OF_INSTANCE_TO_FAIL), but whichever restaurant instance is running at that
 * moment. Otherwise, once a strategy has replaced the original instance, later
 * failures would have nothing to stop.
 */
@Slf4j
@Service
public class FailureInjectionService {
    @Value("${FAILURE_INJECTION}")
    private String failureInjectionStr;
    @Value("${FAILURE_INJECTION_1_START}")
    private Integer failureInjection1Start;
    @Value("${FAILURE_INJECTION_1_DURATION}")
    private Integer failureInjection1Duration;
    @Value("${FAILURE_INJECTION_2_START}")
    private Integer failureInjection2Start;
    @Value("${FAILURE_INJECTION_2_DURATION}")
    private Integer failureInjection2Duration;

    @Autowired
    private AdaptationController adaptationController;
    @Autowired
    private EurekaClient discoveryClient;

    // The instance stopped by the current failure, so the end of that failure
    // restarts the same one (null when no failure is active)
    private String stoppedInstanceId = null;

    @PostConstruct
    public void init() {
        discoveryClient.getApplications(); // force eureka client to initialize
        boolean injectFailure = failureInjectionStr.equalsIgnoreCase("Y");
        log.info("FailureInjectionService initialized, injectFailure? {}", injectFailure ? "YES" : "NO");

        if (injectFailure) {
            Timer timer = new Timer("failureInjectionTimer");
            scheduleFailure(timer, "failure 1", failureInjection1Start, failureInjection1Duration);
            scheduleFailure(timer, "failure 2", failureInjection2Start, failureInjection2Duration);
        }
    }

    /** Schedules one failure: stop a running instance at `start`, restart it after `duration` seconds. */
    private void scheduleFailure(Timer timer, String label, int start, int duration) {
        log.info("{}: start {} s, duration {} s", label, start, duration);
        TimerTask startTask = new TimerTask() {
            @Override
            public void run() {
                injectFailure(label);
            }
        };
        timer.schedule(startTask, start * 1000L);

        if (duration != 0) {
            TimerTask stopTask = new TimerTask() {
                @Override
                public void run() {
                    restoreInstance(label);
                }
            };
            timer.schedule(stopTask, (start + duration) * 1000L);
        }
    }

    private void injectFailure(String label) {
        // Catch everything: an exception inside a TimerTask kills the whole Timer,
        // and then every later failure of the scenario silently never happens
        try {
            String instanceId = runningRestaurantInstance();
            if (instanceId == null) {
                log.warn("{}: no running restaurant instance to stop", label);
                return;
            }
            log.info("{}: stopping {}", label, instanceId);
            adaptationController.stopInstance(instanceId);
            stoppedInstanceId = instanceId;
        } catch (Exception e) {
            log.error("{}: could not stop a restaurant instance", label, e);
        }
    }

    private void restoreInstance(String label) {
        if (stoppedInstanceId == null) {
            log.warn("{}: nothing to restart", label);
            return;
        }
        try {
            log.info("{}: restarting {}", label, stoppedInstanceId);
            adaptationController.startInstance(stoppedInstanceId);
        } catch (Exception e) {
            // RAMSES's instances manager finds containers by name, and the original
            // name (sefa-restaurant-service) is part of every added instance's name.
            // So restarting the ORIGINAL fails when other restaurant containers exist.
            log.error("{}: could not restart {}", label, stoppedInstanceId, e);
        }
        stoppedInstanceId = null;
    }

    /** Id of the first restaurant instance that Eureka reports as UP, or null if there is none. */
    private String runningRestaurantInstance() {
        Application application = discoveryClient.getApplication("RESTAURANT-SERVICE");
        if (application == null) {
            return null;
        }
        for (InstanceInfo instance : application.getInstances()) {
            if (instance.getStatus() == InstanceInfo.InstanceStatus.UP) {
                return instance.getInstanceId();
            }
        }
        return null;
    }
}
