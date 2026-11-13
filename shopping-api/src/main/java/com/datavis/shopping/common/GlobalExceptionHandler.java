package com.datavis.shopping.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * 全局异常处理：任何未捕获异常均按统一响应体返回，避免向前端抛出堆栈。
 * 业务成功码 200，通用失败 500；路径不存在 404、方法不支持 405，便于联调定位。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** 路径不存在（含静态资源与大屏路径）。 */
    @ExceptionHandler(NoResourceFoundException.class)
    public Result<Object> handleNotFound(NoResourceFoundException ex) {
        log.warn("请求路径不存在: {}", ex.getResourcePath());
        return Result.fail(404, "接口不存在: /" + ex.getResourcePath());
    }

    /** 请求方法不支持。 */
    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public Result<Object> handleMethodNotSupported(HttpRequestMethodNotSupportedException ex) {
        log.warn("请求方法不支持: {}", ex.getMessage());
        return Result.fail(405, "请求方法不支持: " + ex.getMethod());
    }

    /** 请求体解析失败或参数非法。 */
    @ExceptionHandler({HttpMessageNotReadableException.class, IllegalArgumentException.class})
    public Result<Object> handleBadRequest(Exception ex) {
        log.warn("请求参数异常: {}", ex.getMessage());
        return Result.fail(500, "请求参数异常: " + ex.getMessage());
    }

    /** 其余未捕获异常统一兜底。 */
    @ExceptionHandler(Exception.class)
    public Result<Object> handleException(Exception ex) {
        log.error("接口处理异常: {}", ex.getMessage(), ex);
        return Result.fail(500, "服务异常: " + ex.getMessage());
    }
}
