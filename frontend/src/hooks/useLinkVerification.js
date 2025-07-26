import { useState } from 'react';
import { cidAPI } from '../api/apiService';

/**
 * 链接验证自定义Hook
 * 提供链接验证状态管理和验证方法
 */
export const useLinkVerification = () => {
    const [linkVerificationStatus, setLinkVerificationStatus] = useState({});

    // 验证单个链接
    const verifySingleLink = async (keyPrefix, linkType, url, forceRefresh = false, cid = null) => {
        const key = `${keyPrefix}-${linkType}`;

        try {
            const response = await cidAPI.verifyLinks([url], forceRefresh, cid);

            if (response.success && response.results.length > 0) {
                const result = response.results[0];
                const status = result.valid ? 'valid' : 'invalid';

                setLinkVerificationStatus(prev => ({
                    ...prev,
                    [key]: status
                }));
            } else {
                setLinkVerificationStatus(prev => ({
                    ...prev,
                    [key]: 'invalid'
                }));
            }
        } catch (error) {
            console.error(`验证${linkType}链接时发生错误:`, error);
            setLinkVerificationStatus(prev => ({
                ...prev,
                [key]: 'invalid'
            }));
        }
    };

    // 验证多个链接
    const verifyLinks = async (dmmResults, keyPrefix = null, forceRefresh = false) => {
        if (!dmmResults || dmmResults.length === 0) return;

        try {
            const verificationPromises = [];

            dmmResults.forEach((result, resultIndex) => {
                // 对于手作修正和数据清洗页面，直接使用resultIndex
                // 对于高清替换页面，使用taskId-resultIndex格式
                const currentKeyPrefix = keyPrefix ? `${keyPrefix}-${resultIndex}` : resultIndex;
                const cid = result.cid; // 从DMM结果中获取CID

                if (result.wallpaper_url?.url) {
                    verificationPromises.push(
                        verifySingleLink(currentKeyPrefix, 'wallpaper', result.wallpaper_url.url, forceRefresh, cid)
                    );
                }
                if (result.cover_url?.url) {
                    verificationPromises.push(
                        verifySingleLink(currentKeyPrefix, 'cover', result.cover_url.url, forceRefresh, cid)
                    );
                }
            });

            if (verificationPromises.length > 0) {
                await Promise.allSettled(verificationPromises);
            }
        } catch (error) {
            console.error('验证链接时发生错误:', error);
        }
    };

    // 刷新链接验证状态
    const refreshLinkVerification = async (dmmResults, keyPrefix = null) => {
        // 先清除验证状态，显示加载状态
        const pendingStatus = {};
        dmmResults.forEach((result, resultIndex) => {
            const currentKeyPrefix = keyPrefix ? `${keyPrefix}-${resultIndex}` : resultIndex;

            if (result.wallpaper_url?.url) {
                pendingStatus[`${currentKeyPrefix}-wallpaper`] = 'pending';
            }
            if (result.cover_url?.url) {
                pendingStatus[`${currentKeyPrefix}-cover`] = 'pending';
            }
        });

        setLinkVerificationStatus(prev => ({ ...prev, ...pendingStatus }));

        // 强制刷新验证
        await verifyLinks(dmmResults, keyPrefix, true);
    };

    // 清除验证状态
    const clearVerificationStatus = () => {
        setLinkVerificationStatus({});
    };

    // 为HdReplacePage提供的包装函数
    const verifyLinksWithTaskId = async (taskId, dmmResults, forceRefresh = false) => {
        await verifyLinks(dmmResults, taskId, forceRefresh);
    };

    const refreshLinkVerificationWithTaskId = async (taskId, dmmResults) => {
        await refreshLinkVerification(dmmResults, taskId);
    };

    return {
        linkVerificationStatus,
        setLinkVerificationStatus,
        verifySingleLink,
        verifyLinks,
        refreshLinkVerification,
        verifyLinksWithTaskId,
        refreshLinkVerificationWithTaskId,
        clearVerificationStatus
    };
};
