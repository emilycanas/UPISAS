package sefa.restclient.domain;

import com.netflix.appinfo.InstanceInfo;
import com.netflix.discovery.EurekaClient;
import com.netflix.discovery.shared.Application;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import javax.annotation.PostConstruct;
import java.util.*;

@Slf4j
@Service
public class PerformanceFakerService {
    @Value("${FAKE_SLOW_ORDERING}")
    private String fakeSlowOrderingStr;
    @Value("${FAKE_SLOW_ORDERING_1_SLEEP}")
    private Double fakeSlowOrdering1Sleep;
    @Value("${FAKE_SLOW_ORDERING_1_START}")
    private Integer fakeSlowOrdering1Start;
    @Value("${FAKE_SLOW_ORDERING_1_DURATION}")
    private Integer fakeSlowOrdering1Duration;
    @Value("${FAKE_SLOW_ORDERING_2_SLEEP}")
    private Double fakeSlowOrdering2Sleep;
    @Value("${FAKE_SLOW_ORDERING_2_START}")
    private Integer fakeSlowOrdering2Start;
    @Value("${FAKE_SLOW_ORDERING_2_DURATION}")
    private Integer fakeSlowOrdering2Duration;
    @Value("${FAKE_SLOW_ORDERING_3_SLEEP}")
    private Double fakeSlowOrdering3Sleep;
    @Value("${FAKE_SLOW_ORDERING_3_START}")
    private Integer fakeSlowOrdering3Start;
    @Value("${FAKE_SLOW_ORDERING_3_DURATION}")
    private Integer fakeSlowOrdering3Duration;
    
    @Value("${FAKE_UNREACHABLE_RESTAURANT_COUNTER}")
    private Integer fakeUnreachableRestaurantCounter;
    @Value("${FAKE_UNREACHABLE_RESTAURANT_DELAY}")
    private Integer fakeUnreachableRestaurantDelay;
    @Value("${FAKE_EXCEPTION_ORDERING}")
    private String fakeExceptionOrderingStr;
    @Value("${FAKE_EXCEPTION_VALUE_1}")
    private Double fakeExceptionValue1;
    @Value("${FAKE_EXCEPTION_VALUE_2}")
    private Double fakeExceptionValue2;
    @Value("${FAKE_EXCEPTION_VALUE_3}")
    private Double fakeExceptionValue3;
    @Value("${FAKE_EXCEPTION_START_1}")
    private Integer fakeExceptionStart1;
    @Value("${FAKE_EXCEPTION_START_2}")
    private Integer fakeExceptionStart2;
    @Value("${FAKE_EXCEPTION_START_3}")
    private Integer fakeExceptionStart3;
    
    @Autowired
    private AdaptationController adaptationController;
    @Autowired
    private EurekaClient discoveryClient;
    
    private Map<String, Double> originalInstancesSleeps;

    @PostConstruct
    public void init() {
        discoveryClient.getApplications(); // force eureka client to initialize
        boolean fakeSlowOrdering = fakeSlowOrderingStr.equalsIgnoreCase("Y");
        boolean fakeExceptionOrdering = fakeExceptionOrderingStr.equalsIgnoreCase("Y");
        log.info("PerformanceFakerService initialized with the following values:");
        log.info("fakeSlowOrdering? {}", fakeSlowOrderingStr.equalsIgnoreCase("Y") ? "YES" : "NO");

        log.info("fakeSlowOrdering1Sleep: {}", fakeSlowOrdering1Sleep);
        log.info("fakeSlowOrdering1Start: {}", fakeSlowOrdering1Start);
        log.info("fakeSlowOrdering1Duration: {}", fakeSlowOrdering1Duration);

        log.info("fakeSlowOrdering2Sleep: {}", fakeSlowOrdering2Sleep);
        log.info("fakeSlowOrdering2Start: {}", fakeSlowOrdering2Start);
        log.info("fakeSlowOrdering2Duration: {}", fakeSlowOrdering2Duration);

        log.info("fakeUnreachableRestaurantCounter: {}", fakeUnreachableRestaurantCounter);
        log.info("fakeUnreachableRestaurantDelay: {}", fakeUnreachableRestaurantDelay);

        if (fakeSlowOrdering) {

            TimerTask fakeSlowOrderingTask1Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 1");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering1Sleep);
                }
            };
            Timer fakeSlowOrderingTimer1Start = new Timer("fakeSlowOrderingTimer1Start");
            fakeSlowOrderingTimer1Start.schedule(fakeSlowOrderingTask1Start, 1000L * fakeSlowOrdering1Start);
            
            TimerTask fakeSlowOrderingTask1End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 1 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer1End = new Timer("fakeSlowOrderingTimer1End");
            fakeSlowOrderingTimer1End.schedule(fakeSlowOrderingTask1End, 1000L * (fakeSlowOrdering1Start+fakeSlowOrdering1Duration));

            TimerTask fakeSlowOrderingTask2Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 2");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering2Sleep);
                }
            };
            Timer fakeSlowOrderingTimer2Start = new Timer("fakeSlowOrderingTimer2Start");
            fakeSlowOrderingTimer2Start.schedule(fakeSlowOrderingTask2Start, 1000L * fakeSlowOrdering2Start);
            
            TimerTask fakeSlowOrderingTask2End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 2 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer2End = new Timer("fakeSlowOrderingTimer2End");
            fakeSlowOrderingTimer2End.schedule(fakeSlowOrderingTask2End, 1000L * (fakeSlowOrdering2Start+fakeSlowOrdering2Duration));

            // Task 3
            TimerTask fakeSlowOrderingTask3Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 3");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering3Sleep);
                }
            };
            Timer fakeSlowOrderingTimer3Start = new Timer("fakeSlowOrderingTimer3Start");
            fakeSlowOrderingTimer3Start.schedule(fakeSlowOrderingTask3Start, 1000L * fakeSlowOrdering3Start);

            TimerTask fakeSlowOrderingTask3End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 3 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer3End = new Timer("fakeSlowOrderingTimer3End");
            fakeSlowOrderingTimer3End.schedule(fakeSlowOrderingTask3End, 1000L * (fakeSlowOrdering3Start+fakeSlowOrdering3Duration));
	}

        if (fakeUnreachableRestaurantCounter != 0) {
            TimerTask fakeUnreachableRestaurantTask = new TimerTask() {
                public void run() {
                    log.info("Faking unreachable restaurant");
                    try {
                        adaptationController.setFakeCounter(fakeUnreachableRestaurantCounter);
                    } catch (Exception e) {
                        log.error("Error while faking unreachable restaurant", e);
                        System.exit(1);
                    }
                }
            };
            Timer fakeUnreachableRestaurantTimer = new Timer("fakeUnreachableRestaurantTimer");
            fakeUnreachableRestaurantTimer.schedule(fakeUnreachableRestaurantTask, 1000L * 60 * fakeUnreachableRestaurantDelay);
        }

        if (fakeExceptionOrdering) {
            Integer lastPos = discoveryClient.getApplication("ORDERING-SERVICE").size() - 1;
            String orderUrl = discoveryClient.getApplication("ORDERING-SERVICE").getInstances().get(lastPos).getHomePageUrl();

            Timer timer = new Timer();
            TimerTask fakeExcpetion = new TimerTask() {
                @Override
                public void run() {
                    log.info("Faking the FIRST exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue1);
                    adaptationController.updateOrderingException(orderUrl, fakeExceptionValue1);
                }
            };
            timer.schedule(fakeExcpetion, 1000L * fakeExceptionStart1);

            if (fakeExceptionStart2 != 0) {
                Timer timer2 = new Timer();
                TimerTask fakeExcpetion2 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the SECOND exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue2);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue2);
                    }
                };
                timer2.schedule(fakeExcpetion2, 1000L * fakeExceptionStart2);
            }
            if (fakeExceptionStart3 != 0) {
                Timer timer3 = new Timer();
                TimerTask fakeExcpetion3 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the THIRD exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue3);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue3);
                    }
                };
                timer3.schedule(fakeExcpetion3, 1000L * fakeExceptionStart3);
            }
        }
    }

    /**
     * Current sleep of every ordering instance that answers.
     * Changed from the RAMSES original: an instance that does not answer (still
     * booting, or stopped but still in Eureka) is skipped. The original called
     * System.exit(1) here, which ended the whole scenario, so no more requests
     * were sent for the rest of the run.
     */
    private Map<String, Double> getSleepForOrderingServiceInstances() {
        Map<String, Double> instancesOriginalSleep = new HashMap<>();
        for (InstanceInfo instance : orderingInstances()) {
            String url = "http://" + instance.getHostName() + ":" + instance.getPort() + "/rest/instrumentation/sleepMean";
            try {
                RestTemplate restTemplate = new RestTemplate();
                Double sleep = Double.parseDouble(Objects.requireNonNull(restTemplate.getForObject(url, String.class)));
                instancesOriginalSleep.put(instance.getInstanceId(), sleep);
                log.info("Initial sleep for instance {}: {}", instance.getInstanceId(), sleep);
            } catch (Exception e) {
                log.warn("Skipping ordering instance {}: it did not answer ({})", instance.getInstanceId(), e.getMessage());
            }
        }
        return instancesOriginalSleep;
    }

    /** Sets the sleep of every ordering instance to its original sleep + sleepMean, skipping instances that do not answer. */
    private void changeSleepForOrderingServiceInstances(Double sleepMean) {
        for (InstanceInfo instance : orderingInstances()) {
            Double originalSleep = originalInstancesSleeps.get(instance.getInstanceId());
            if (originalSleep == null) {
                continue;   // was not reachable when the slowdown started
            }
            String url = "http://" + instance.getHostName() + ":" + instance.getPort() + "/rest/instrumentation/sleepMean?sleepMean={sleepMean}";
            log.info("Changing sleep for instance {} from {} to {}", instance.getInstanceId(), originalSleep, sleepMean + originalSleep);
            try {
                RestTemplate restTemplate = new RestTemplate();
                restTemplate.put(url, null, Map.of("sleepMean", String.valueOf(originalSleep + sleepMean)));
            } catch (Exception e) {
                log.warn("Could not change the sleep of ordering instance {} (it may have been shut down): {}", instance.getInstanceId(), e.getMessage());
            }
        }
    }

    /** The ordering instances Eureka knows about (an empty list if none). */
    private List<InstanceInfo> orderingInstances() {
        Application application = discoveryClient.getApplication("ORDERING-SERVICE");
        if (application == null) {
            return new ArrayList<>();
        }
        return application.getInstances();
    }

}
