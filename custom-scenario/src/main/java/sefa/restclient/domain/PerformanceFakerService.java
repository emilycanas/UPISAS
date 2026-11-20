package sefa.restclient.domain;

import com.netflix.discovery.EurekaClient;
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
    @Value("${FAKE_SLOW_ORDERING_4_SLEEP}")
    private Double fakeSlowOrdering4Sleep;
    @Value("${FAKE_SLOW_ORDERING_4_START}")
    private Integer fakeSlowOrdering4Start;
    @Value("${FAKE_SLOW_ORDERING_4_DURATION}")
    private Integer fakeSlowOrdering4Duration;
    @Value("${FAKE_SLOW_ORDERING_5_SLEEP}")
    private Double fakeSlowOrdering5Sleep;
    @Value("${FAKE_SLOW_ORDERING_5_START}")
    private Integer fakeSlowOrdering5Start;
    @Value("${FAKE_SLOW_ORDERING_5_DURATION}")
    private Integer fakeSlowOrdering5Duration;
    @Value("${FAKE_SLOW_ORDERING_6_SLEEP}")
    private Double fakeSlowOrdering6Sleep;
    @Value("${FAKE_SLOW_ORDERING_6_START}")
    private Integer fakeSlowOrdering6Start;
    @Value("${FAKE_SLOW_ORDERING_6_DURATION}")
    private Integer fakeSlowOrdering6Duration;
    @Value("${FAKE_SLOW_ORDERING_7_SLEEP}")
    private Double fakeSlowOrdering7Sleep;
    @Value("${FAKE_SLOW_ORDERING_7_START}")
    private Integer fakeSlowOrdering7Start;
    @Value("${FAKE_SLOW_ORDERING_7_DURATION}")
    private Integer fakeSlowOrdering7Duration;
    @Value("${FAKE_SLOW_ORDERING_8_SLEEP}")
    private Double fakeSlowOrdering8Sleep;
    @Value("${FAKE_SLOW_ORDERING_8_START}")
    private Integer fakeSlowOrdering8Start;
    @Value("${FAKE_SLOW_ORDERING_8_DURATION}")
    private Integer fakeSlowOrdering8Duration;
    @Value("${FAKE_SLOW_ORDERING_9_SLEEP}")
    private Double fakeSlowOrdering9Sleep;
    @Value("${FAKE_SLOW_ORDERING_9_START}")
    private Integer fakeSlowOrdering9Start;
    @Value("${FAKE_SLOW_ORDERING_9_DURATION}")
    private Integer fakeSlowOrdering9Duration;
    @Value("${FAKE_SLOW_ORDERING_10_SLEEP}")
    private Double fakeSlowOrdering10Sleep;
    @Value("${FAKE_SLOW_ORDERING_10_START}")
    private Integer fakeSlowOrdering10Start;
    @Value("${FAKE_SLOW_ORDERING_10_DURATION}")
    private Integer fakeSlowOrdering10Duration;
    
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
    @Value("${FAKE_EXCEPTION_VALUE_4}")
    private Double fakeExceptionValue4;
    @Value("${FAKE_EXCEPTION_VALUE_5}")
    private Double fakeExceptionValue5;
    @Value("${FAKE_EXCEPTION_VALUE_6}")
    private Double fakeExceptionValue6;
    @Value("${FAKE_EXCEPTION_VALUE_7}")
    private Double fakeExceptionValue7;
    @Value("${FAKE_EXCEPTION_VALUE_8}")
    private Double fakeExceptionValue8;
    @Value("${FAKE_EXCEPTION_VALUE_9}")
    private Double fakeExceptionValue9;
    @Value("${FAKE_EXCEPTION_START_1}")
    private Integer fakeExceptionStart1;
    @Value("${FAKE_EXCEPTION_START_2}")
    private Integer fakeExceptionStart2;
    @Value("${FAKE_EXCEPTION_START_3}")
    private Integer fakeExceptionStart3;
    @Value("${FAKE_EXCEPTION_START_4}")
    private Integer fakeExceptionStart4;
    @Value("${FAKE_EXCEPTION_START_5}")
    private Integer fakeExceptionStart5;
    @Value("${FAKE_EXCEPTION_START_6}")
    private Integer fakeExceptionStart6;
    @Value("${FAKE_EXCEPTION_START_7}")
    private Integer fakeExceptionStart7;
    @Value("${FAKE_EXCEPTION_START_8}")
    private Integer fakeExceptionStart8;
    @Value("${FAKE_EXCEPTION_START_9}")
    private Integer fakeExceptionStart9;
    
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

            // Task 4
            TimerTask fakeSlowOrderingTask4Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 4");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering4Sleep);
                }
            };
            Timer fakeSlowOrderingTimer4Start = new Timer("fakeSlowOrderingTimer4Start");
            fakeSlowOrderingTimer4Start.schedule(fakeSlowOrderingTask4Start, 1000L * fakeSlowOrdering4Start);

            TimerTask fakeSlowOrderingTask4End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 4 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer4End = new Timer("fakeSlowOrderingTimer4End");
            fakeSlowOrderingTimer4End.schedule(fakeSlowOrderingTask4End, 1000L * (fakeSlowOrdering4Start+fakeSlowOrdering4Duration));

            // Task 5
            TimerTask fakeSlowOrderingTask5Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 5");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering5Sleep);
                }
            };
            Timer fakeSlowOrderingTimer5Start = new Timer("fakeSlowOrderingTimer5Start");
            fakeSlowOrderingTimer5Start.schedule(fakeSlowOrderingTask5Start, 1000L * fakeSlowOrdering5Start);

            TimerTask fakeSlowOrderingTask5End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 5 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer5End = new Timer("fakeSlowOrderingTimer5End");
            fakeSlowOrderingTimer5End.schedule(fakeSlowOrderingTask5End, 1000L * (fakeSlowOrdering5Start+fakeSlowOrdering5Duration));

            // Task 6
            TimerTask fakeSlowOrderingTask6Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 6");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering6Sleep);
                }
            };
            Timer fakeSlowOrderingTimer6Start = new Timer("fakeSlowOrderingTimer6Start");
            fakeSlowOrderingTimer6Start.schedule(fakeSlowOrderingTask6Start, 1000L * fakeSlowOrdering6Start);

            TimerTask fakeSlowOrderingTask6End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 6 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer6End = new Timer("fakeSlowOrderingTimer6End");
            fakeSlowOrderingTimer6End.schedule(fakeSlowOrderingTask6End, 1000L * (fakeSlowOrdering6Start+fakeSlowOrdering6Duration));

            // Task 7
            TimerTask fakeSlowOrderingTask7Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 7");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering7Sleep);
                }
            };
            Timer fakeSlowOrderingTimer7Start = new Timer("fakeSlowOrderingTimer7Start");
            fakeSlowOrderingTimer7Start.schedule(fakeSlowOrderingTask7Start, 1000L * fakeSlowOrdering7Start);

            TimerTask fakeSlowOrderingTask7End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 7 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer7End = new Timer("fakeSlowOrderingTimer7End");
            fakeSlowOrderingTimer7End.schedule(fakeSlowOrderingTask7End, 1000L * (fakeSlowOrdering7Start+fakeSlowOrdering7Duration));

            // Task 8
            TimerTask fakeSlowOrderingTask8Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 8");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering8Sleep);
                }
            };
            Timer fakeSlowOrderingTimer8Start = new Timer("fakeSlowOrderingTimer8Start");
            fakeSlowOrderingTimer8Start.schedule(fakeSlowOrderingTask8Start, 1000L * fakeSlowOrdering8Start);

            TimerTask fakeSlowOrderingTask8End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 8 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer8End = new Timer("fakeSlowOrderingTimer8End");
            fakeSlowOrderingTimer8End.schedule(fakeSlowOrderingTask8End, 1000L * (fakeSlowOrdering8Start+fakeSlowOrdering8Duration));

            // Task 9
            TimerTask fakeSlowOrderingTask9Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 9");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering9Sleep);
                }
            };
            Timer fakeSlowOrderingTimer9Start = new Timer("fakeSlowOrderingTimer9Start");
            fakeSlowOrderingTimer9Start.schedule(fakeSlowOrderingTask9Start, 1000L * fakeSlowOrdering9Start);

            TimerTask fakeSlowOrderingTask9End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 9 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer9End = new Timer("fakeSlowOrderingTimer9End");
            fakeSlowOrderingTimer9End.schedule(fakeSlowOrderingTask9End, 1000L * (fakeSlowOrdering9Start+fakeSlowOrdering9Duration));

            // Task 10
            TimerTask fakeSlowOrderingTask10Start = new TimerTask() {
                public void run() {
                    log.info("START: Faking slow ordering 10");
                    originalInstancesSleeps = getSleepForOrderingServiceInstances();
                    changeSleepForOrderingServiceInstances(fakeSlowOrdering10Sleep);
                }
            };
            Timer fakeSlowOrderingTimer10Start = new Timer("fakeSlowOrderingTimer10Start");
            fakeSlowOrderingTimer10Start.schedule(fakeSlowOrderingTask10Start, 1000L * fakeSlowOrdering10Start);

            TimerTask fakeSlowOrderingTask10End = new TimerTask() {
                public void run() {
                    log.info("END: Faking slow ordering 10 end");
                    changeSleepForOrderingServiceInstances(0.0);
                }
            };
            Timer fakeSlowOrderingTimer10End = new Timer("fakeSlowOrderingTimer10End");
            fakeSlowOrderingTimer10End.schedule(fakeSlowOrderingTask10End, 1000L * (fakeSlowOrdering10Start+fakeSlowOrdering10Duration));
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
            if (fakeExceptionStart4 != 0) {
                Timer timer4 = new Timer();
                TimerTask fakeExcpetion4 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the FOURTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue4);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue4);
                    }
                };
                timer4.schedule(fakeExcpetion4, 1000L * fakeExceptionStart4);
            }
            if (fakeExceptionStart5 != 0) {
                Timer timer5 = new Timer();
                TimerTask fakeExcpetion5 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the FIFTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue5);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue5);
                    }
                };
                timer5.schedule(fakeExcpetion5, 1000L * fakeExceptionStart5);
            }
            if (fakeExceptionStart6 != 0) {
                Timer timer6 = new Timer();
                TimerTask fakeExcpetion6 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the SIXTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue6);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue6);
                    }
                };
                timer6.schedule(fakeExcpetion6, 1000L * fakeExceptionStart6);
            }
            if (fakeExceptionStart7 != 0) {
                Timer timer7 = new Timer();
                TimerTask fakeExcpetion7 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the SEVENTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue7);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue7);
                    }
                };
                timer7.schedule(fakeExcpetion7, 1000L * fakeExceptionStart7);
            }
            if (fakeExceptionStart8 != 0) {
                Timer timer8 = new Timer();
                TimerTask fakeExcpetion8 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the EIGTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue8);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue8);
                    }
                };
                timer8.schedule(fakeExcpetion8, 1000L * fakeExceptionStart8);
            }
            if (fakeExceptionStart9 != 0) {
                Timer timer9 = new Timer();
                TimerTask fakeExcpetion9 = new TimerTask() {
                    @Override
                    public void run() {
                        log.info("Faking the NINTH exception for sefa-ordering-service url: {} to a value of {}", orderUrl,fakeExceptionValue9);
                        adaptationController.updateOrderingException(orderUrl, fakeExceptionValue9);
                    }
                };
                timer9.schedule(fakeExcpetion9, 1000L * fakeExceptionStart9);
            }
        }
    }

    private Map<String, Double> getSleepForOrderingServiceInstances() {
        Map<String, Double> instancesOriginalSleep = new HashMap<>();
        try {
            discoveryClient.getApplication("ORDERING-SERVICE").getInstances().forEach(instance -> {
                String url = "http://" + instance.getHostName() + ":" + instance.getPort() + "/rest/instrumentation/sleepMean";
                RestTemplate restTemplate = new RestTemplate();
                instancesOriginalSleep.put(instance.getInstanceId(), Double.parseDouble(Objects.requireNonNull(restTemplate.getForObject(url, String.class))));
                log.info("Initial sleep for instance {}: {}", instance.getInstanceId(), instancesOriginalSleep.get(instance.getInstanceId()));
            });
        } catch (Exception e) {
            log.error("Error while slowing down ordering", e);
            System.exit(1);
        }
        return instancesOriginalSleep;
    }
    
    private void changeSleepForOrderingServiceInstances(Double sleepMean) {
        try {
            discoveryClient.getApplication("ORDERING-SERVICE").getInstances().forEach(instance -> {
                Double originalSleep = originalInstancesSleeps.get(instance.getInstanceId());
                if (originalSleep == null) return;

                String url = "http://" + instance.getHostName() + ":" + instance.getPort() + "/rest/instrumentation/sleepMean?sleepMean={sleepMean}";
                RestTemplate restTemplate = new RestTemplate();
                log.info("Changing sleep for instance {} from {} to {}", instance.getInstanceId(), originalSleep, sleepMean+originalSleep);
                try {
                    restTemplate.put(url, null, Map.of("sleepMean", String.valueOf(originalSleep+sleepMean)));
                } catch (Exception e) {
                    if (sleepMean == 0.0) {
                        log.error("Error while restoring ordering. The instance {} could have been shutdown", instance.getInstanceId());
                    } else {
                        log.error("Error while slowing down ordering", e);
                        System.exit(1);
                    }
                }
            });
        } catch (Exception e) {
            log.error("Error while slowing down ordering", e);
            System.exit(1);
        }
    }

}
