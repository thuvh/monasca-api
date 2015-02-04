select T1.* ,group_concat(distinct notification_method.name) as alarmNames, 
           group_concat(distinct alarm_action.alarm_state) as states, group_concat(distinct alarm_action.action_id) as notificationIds from  (select distinct alarm_definition.id,tenant_id,
           name,description, severity, expression, match_by, actions_enabled, alarm_definition.created_at, alarm_definition.updated_at,
            alarm_definition.deleted_at from alarm_definition inner join sub_alarm_definition sub on alarm_definition.id = sub.alarm_definition_id
            left outer join sub_alarm_definition_dimension dim on sub.id = dim.sub_alarm_definition_id where tenant_id = "efc8f0edd7e04ceaa4f8e9d8d21ad4f0"
            and deleted_at is NULL  order by  alarm_definition.created_at ) AS T1 INNER JOIN alarm_action ON T1.id=alarm_action.alarm_definition_id
            INNER JOIN notification_method ON alarm_action.action_id=notification_method.id

            UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM,UNDETERMINED,OK,ALARM

            415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-57c8e65d274d,415e0320-13d4-4bed-9ccd-5

            select T1.* ,group_concat(notification_method.name) as alarmNames, 
           group_concat(alarm_action.alarm_state) as states, group_concat(alarm_action.action_id) as notificationIds from  (select distinct alarm_definition.id,tenant_id,
           name,description, severity, expression, match_by, actions_enabled, alarm_definition.created_at, alarm_definition.updated_at,
            alarm_definition.deleted_at from alarm_definition inner join sub_alarm_definition sub on alarm_definition.id = sub.alarm_definition_id
            left outer join sub_alarm_definition_dimension dim on sub.id = dim.sub_alarm_definition_id where tenant_id = "bob"
            and deleted_at is NULL  order by  alarm_definition.created_at ) AS T1 INNER JOIN alarm_action ON T1.id=alarm_action.alarm_definition_id
            INNER JOIN notification_method ON alarm_action.action_id=notification_method.id

            /*
				GOOD ONE
            */
            select T1.* ,group_concat(distinct notification_method.name) as alarmNames,           
              group_concat(distinct alarm_action.alarm_state) as states, group_concat(distinct alarm_action.action_id) 
              as notificationIds from  (select distinct alarm_definition.id,tenant_id,            name,description, severity, 
              	expression, match_by, actions_enabled, alarm_definition.created_at, alarm_definition.updated_at,            
              	 alarm_definition.deleted_at from alarm_definition inner join sub_alarm_definition sub on 
              	 alarm_definition.id = sub.alarm_definition_id             left outer join sub_alarm_definition_dimension dim 
              	 on sub.id = dim.sub_alarm_definition_id where tenant_id = "efc8f0edd7e04ceaa4f8e9d8d21ad4f0"           
              	   and deleted_at is NULL  order by  alarm_definition.created_at ) AS T1 INNER JOIN alarm_action
              	    ON T1.id=alarm_action.alarm_definition_id  
                       INNER JOIN notification_method ON alarm_action.action_id=notification_method.id group by T1.id;
----------final and good one 
                       select T1.* ,group_concat(notification_method.name) as alarmNames,            
                        group_concat( alarm_action.alarm_state) as states, group_concat(alarm_action.action_id) as notificationIds 
                        from  (select distinct alarm_definition.id,tenant_id,        
                            name,description, severity, expression, match_by, actions_enabled, alarm_definition.created_at, 
                            alarm_definition.updated_at, alarm_definition.deleted_at from alarm_definition
                             inner join sub_alarm_definition sub
                             on alarm_definition.id = sub.alarm_definition_id             
                             left outer join sub_alarm_definition_dimension dim 
                 on sub.id = dim.sub_alarm_definition_id where tenant_id = "efc8f0edd7e04ceaa4f8e9d8d21ad4f0"            
                 and deleted_at is NULL  order by  alarm_definition.created_at ) AS T1 INNER JOIN alarm_action 
                        ON T1.id=alarm_action.alarm_definition_id      
                              INNER JOIN notification_method ON alarm_action.action_id=notification_method.id group by T1.id;

findbyid

select alarm_definition.*, group_concat(notification_method.name)as alarmNames,"
  + "group_concat(alarm_action.action_id) as notificationIds,group_concat(alarm_action.alarm_state) as states "
  + "from alarm_definition, alarm_action,notification_method where 
  alarm_definition.id=alarm_action.alarm_definition_id "
  + "and alarm_action.action_id=notification_method.id and 
  alarm_definition.tenant_id=:tenantId and alarm_definition.id=:alarmDefId and
   alarm_definition.deleted_at is NULL group by alarm_definition.id";





