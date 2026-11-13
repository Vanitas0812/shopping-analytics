package com.datavis.shopping.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.ViewControllerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 大屏静态资源访问配置：把 /dashboard-a/ 直接映射到 index.html，
 * 保证浏览器用目录形式访问也能正常打开大屏。
 */
@Configuration
public class DashboardViewConfig implements WebMvcConfigurer {

    @Override
    public void addViewControllers(ViewControllerRegistry registry) {
        registry.addViewController("/dashboard-a").setViewName("forward:/dashboard-a/index.html");
        registry.addViewController("/dashboard-a/").setViewName("forward:/dashboard-a/index.html");
    }
}
